// SPDX-License-Identifier: Apache-2.0
// Original traversal: Copyright 2001-2025 The Apache Software Foundation.
// Position traversal adapted from Apache Lucene 10.4.0 SloppyPhraseMatcher.
// Rust adaptation uses a bounded, lazily updated standard-library heap.
// Upstream license and notices: docs/licenses/lucene/.
// See docs/rust-port/native-ranking-audit-2026-09-10.md for source and evidence.

use std::cmp::Reverse;
use std::collections::{BTreeMap, BinaryHeap};

type Entry = Reverse<(i64, u32, usize, usize)>;

pub(super) struct Matcher {
    offsets: Vec<u32>,
    groups: Vec<Vec<usize>>,
    group_for: Vec<usize>,
    cursors: Vec<usize>,
    queued: Vec<bool>,
    heap: BinaryHeap<Entry>,
    end: i64,
}

impl Matcher {
    pub(super) fn new(term_ids: &[usize], offsets: &[u32]) -> Self {
        assert_eq!(term_ids.len(), offsets.len());
        let mut grouped = BTreeMap::<usize, Vec<usize>>::new();
        for (ordinal, term) in term_ids.iter().enumerate() {
            grouped.entry(*term).or_default().push(ordinal);
        }
        let mut groups = grouped.into_values().collect::<Vec<_>>();
        let mut group_for = vec![0; offsets.len()];
        for (group_id, group) in groups.iter_mut().enumerate() {
            group.sort_unstable_by_key(|&ordinal| (offsets[ordinal], ordinal));
            for &ordinal in group.iter() {
                group_for[ordinal] = group_id;
            }
        }
        Self {
            offsets: offsets.to_vec(),
            groups,
            group_for,
            cursors: vec![0; offsets.len()],
            queued: vec![false; offsets.len()],
            heap: BinaryHeap::with_capacity(offsets.len() * 2),
            end: i64::MIN,
        }
    }

    fn position(&self, ordinal: usize, positions: &[Vec<u32>]) -> i64 {
        i64::from(positions[ordinal][self.cursors[ordinal]]) - i64::from(self.offsets[ordinal])
    }

    fn entry(&self, ordinal: usize, positions: &[Vec<u32>]) -> Entry {
        Reverse((
            self.position(ordinal, positions),
            self.offsets[ordinal],
            ordinal,
            self.cursors[ordinal],
        ))
    }

    fn enqueue(&mut self, ordinal: usize, positions: &[Vec<u32>]) {
        self.queued[ordinal] = true;
        self.heap.push(self.entry(ordinal, positions));
        // Repeated-term collisions can move an entry still in the queue.
        // Lazy invalidation is bounded so long documents cannot grow the heap indefinitely.
        if self.heap.len() > self.offsets.len() * 2 {
            self.heap.clear();
            for ordinal in 0..self.offsets.len() {
                if self.queued[ordinal] {
                    self.heap.push(self.entry(ordinal, positions));
                }
            }
        }
    }

    fn discard_stale(&mut self) {
        while let Some(Reverse((_, _, ordinal, cursor))) = self.heap.peek().copied() {
            if self.queued[ordinal] && self.cursors[ordinal] == cursor {
                break;
            }
            self.heap.pop();
        }
    }

    fn pop(&mut self) -> usize {
        self.discard_stale();
        let Reverse((_, _, ordinal, _)) = self.heap.pop().unwrap();
        self.queued[ordinal] = false;
        ordinal
    }

    fn first_position(&mut self) -> i64 {
        self.discard_stale();
        self.heap.peek().unwrap().0 .0
    }

    fn advance(&mut self, ordinal: usize, positions: &[Vec<u32>]) -> bool {
        if self.cursors[ordinal] + 1 >= positions[ordinal].len() {
            return false;
        }
        self.cursors[ordinal] += 1;
        self.end = self.end.max(self.position(ordinal, positions));
        if self.queued[ordinal] {
            self.enqueue(ordinal, positions);
        }
        true
    }

    fn resolve_collisions(&mut self, mut ordinal: usize, positions: &[Vec<u32>]) -> bool {
        loop {
            let group = &self.groups[self.group_for[ordinal]];
            let actual = positions[ordinal][self.cursors[ordinal]];
            let Some(other) = group
                .iter()
                .copied()
                .find(|&other| other != ordinal && positions[other][self.cursors[other]] == actual)
            else {
                return true;
            };
            if (self.position(other, positions), self.offsets[other])
                < (self.position(ordinal, positions), self.offsets[ordinal])
            {
                ordinal = other;
            }
            if !self.advance(ordinal, positions) {
                return false;
            }
        }
    }

    pub(super) fn frequency(&mut self, positions: &[Vec<u32>], slop: u32) -> f32 {
        self.evaluate(positions, slop, false)
    }

    pub(super) fn matches(&mut self, positions: &[Vec<u32>], slop: u32) -> bool {
        self.evaluate(positions, slop, true) > 0.0
    }

    fn evaluate(&mut self, positions: &[Vec<u32>], slop: u32, first_only: bool) -> f32 {
        assert_eq!(positions.len(), self.offsets.len());
        self.heap.clear();
        self.cursors.fill(0);
        self.queued.fill(false);
        self.end = i64::MIN;
        if positions.is_empty() || positions.iter().any(Vec::is_empty) {
            return 0.0;
        }
        if positions.len() == 1 {
            return positions[0].len() as f32;
        }
        for group in &self.groups {
            for (cursor, &ordinal) in group.iter().enumerate() {
                if cursor >= positions[ordinal].len() {
                    return 0.0;
                }
                self.cursors[ordinal] = cursor;
            }
        }
        for ordinal in 0..positions.len() {
            self.end = self.end.max(self.position(ordinal, positions));
            self.enqueue(ordinal, positions);
        }
        let mut frequency = 0.0;
        'matches: loop {
            let mut ordinal = self.pop();
            let mut length = self.end - self.position(ordinal, positions);
            let mut next = self.first_position();
            while self.advance(ordinal, positions) && self.resolve_collisions(ordinal, positions) {
                if self.position(ordinal, positions) > next {
                    self.enqueue(ordinal, positions);
                    if length <= i64::from(slop) {
                        if first_only {
                            return 1.0;
                        }
                        frequency += 1.0 / (1.0 + length as f32);
                        continue 'matches;
                    }
                    ordinal = self.pop();
                    next = self.first_position();
                    length = self.end - self.position(ordinal, positions);
                } else {
                    length = length.min(self.end - self.position(ordinal, positions));
                }
            }
            if length <= i64::from(slop) {
                frequency += 1.0 / (1.0 + length as f32);
            }
            break;
        }
        frequency
    }
}

#[cfg(test)]
mod tests {
    use super::Matcher;

    #[test]
    fn repeated_positions_bound_heap_and_reset_between_documents() {
        let mut matcher = Matcher::new(&[0, 0], &[0, 1]);
        let positions = (0..10_000).map(|n| n * 2).collect::<Vec<_>>();
        assert_eq!(
            matcher.frequency(&[positions.clone(), positions], 1),
            4999.5
        );
        assert!(matcher.heap.len() <= 4);
        assert_eq!(matcher.frequency(&[vec![0], vec![0]], 100), 0.0);
        assert_eq!(matcher.frequency(&[vec![0, 1], vec![0, 1]], 0), 1.0);
        assert_eq!(matcher.frequency(&[vec![], vec![]], 100), 0.0);
        assert_eq!(matcher.frequency(&[vec![0, 2], vec![0, 2]], 1), 0.5);
    }

    #[test]
    fn shifted_positions_preserve_reordered_phrase_frequency() {
        let mut matcher = Matcher::new(&[0, 1, 2], &[0, 1, 2]);
        for base in [0, 1, 100, 2_147_483_517] {
            let positions = vec![vec![base], vec![base + 2], vec![base + 1]];
            assert_eq!(matcher.frequency(&positions, 1), 0.0);
            assert_eq!(matcher.frequency(&positions, 2), 1.0 / 3.0);
        }
    }
}
