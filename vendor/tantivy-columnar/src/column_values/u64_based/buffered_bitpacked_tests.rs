use std::io::{self, ErrorKind, Write};

use super::*;
use crate::column_values::u64_based::StatsCollector;

fn stats_for(values: &[u64]) -> ColumnStats {
    let mut collector = StatsCollector::default();
    for &value in values {
        collector.collect(value);
    }
    collector.stats()
}

// This deliberately retains the serializer that preceded buffering so that byte
// compatibility is checked against behavior rather than an independently derived format.
fn serialize_original(
    stats: &ColumnStats,
    values: &[u64],
    writer: &mut dyn Write,
) -> io::Result<()> {
    stats.serialize(writer)?;
    let num_bits = num_bits(stats);
    let mut bit_packer = BitPacker::new();
    let divider = DividerU64::divide_by(stats.gcd.get());
    for &value in values {
        bit_packer.write(divider.divide(value - stats.min_value), num_bits, writer)?;
    }
    bit_packer.close(writer)
}

fn serialize_current(
    stats: &ColumnStats,
    values: &[u64],
    writer: &mut dyn Write,
) -> io::Result<()> {
    BitpackedCodecEstimator.serialize(stats, &mut values.iter().copied(), writer)
}

fn assert_matches_original_and_decodes(values: &[u64]) {
    let stats = stats_for(values);
    let mut original = Vec::new();
    serialize_original(&stats, values, &mut original).unwrap();

    let mut current = Vec::new();
    serialize_current(&stats, values, &mut current).unwrap();
    assert_eq!(current, original, "bit width {}", num_bits(&stats));

    let reader = BitpackedCodec::load(OwnedBytes::new(current)).unwrap();
    assert_eq!(reader.num_vals(), values.len() as u32);
    for (row_id, &value) in values.iter().enumerate() {
        assert_eq!(reader.get_val(row_id as u32), value, "row {row_id}");
    }
}

#[test]
fn buffered_serializer_matches_original_for_every_supported_bit_width() {
    assert_matches_original_and_decodes(&[]);
    assert_matches_original_and_decodes(&[u64::MAX]);

    for bit_width in 1..=56 {
        let amplitude = 1u64 << (bit_width - 1);
        let min_value = 17;
        let values = [min_value, min_value + 1, min_value + amplitude];
        let stats = stats_for(&values);
        assert_eq!(num_bits(&stats), bit_width);
        assert_matches_original_and_decodes(&values);
        let large: Vec<_> = values
            .into_iter()
            .cycle()
            .take(65536 / bit_width as usize + 3)
            .collect();
        assert_matches_original_and_decodes(&large);
    }

    let extremes = [0, 1, u64::MAX];
    assert_eq!(num_bits(&stats_for(&extremes)), 64);
    assert_matches_original_and_decodes(&extremes);
    let gcd_values: Vec<_> = [100, 110, 120].into_iter().cycle().take(40000).collect();
    assert_eq!(stats_for(&gcd_values).gcd.get(), 10);
    assert_matches_original_and_decodes(&gcd_values);
}

#[test]
fn buffered_serializer_matches_original_across_8kib_payload_boundary() {
    for length in [1023usize, 1024, 1025] {
        let values = (0..length)
            .map(|index| match index % 3 {
                0 => 0,
                1 => 1,
                _ => u64::MAX,
            })
            .collect::<Vec<_>>();
        assert_eq!(num_bits(&stats_for(&values)), 64);
        assert_matches_original_and_decodes(&values);
    }
}

#[derive(Clone, Copy)]
enum Failure {
    Permanent,
    WriteZero,
}

struct ControlledWriter {
    bytes: Vec<u8>,
    short_limit: Option<usize>,
    interrupt_once: bool,
    interrupt_on_call: Option<usize>,
    failure_on_call: Option<usize>,
    failure: Option<Failure>,
    failed: bool,
    calls: usize,
    calls_after_failure: usize,
    flushes: usize,
}

impl ControlledWriter {
    fn normal() -> Self {
        Self {
            bytes: Vec::new(),
            short_limit: None,
            interrupt_once: false,
            interrupt_on_call: None,
            failure_on_call: None,
            failure: None,
            failed: false,
            calls: 0,
            calls_after_failure: 0,
            flushes: 0,
        }
    }

    fn failing_on(call: usize, failure: Failure) -> Self {
        Self {
            failure_on_call: Some(call),
            failure: Some(failure),
            ..Self::normal()
        }
    }
}

impl Write for ControlledWriter {
    fn write(&mut self, buffer: &[u8]) -> io::Result<usize> {
        self.calls += 1;
        if self.failed {
            self.calls_after_failure += 1;
            return Err(io::Error::new(
                ErrorKind::BrokenPipe,
                "write retried after failure",
            ));
        }
        if self.interrupt_once || self.interrupt_on_call == Some(self.calls) {
            self.interrupt_once = false;
            return Err(io::Error::new(ErrorKind::Interrupted, "interrupted"));
        }
        if self.failure_on_call == Some(self.calls) {
            self.failed = true;
            return match self.failure.unwrap() {
                Failure::Permanent => {
                    Err(io::Error::new(ErrorKind::BrokenPipe, "permanent failure"))
                }
                Failure::WriteZero => Ok(0),
            };
        }

        let written = self.short_limit.unwrap_or(buffer.len()).min(buffer.len());
        self.bytes.extend_from_slice(&buffer[..written]);
        Ok(written)
    }

    fn flush(&mut self) -> io::Result<()> {
        self.flushes += 1;
        Ok(())
    }
}

fn stats_write_calls(stats: &ColumnStats) -> usize {
    let mut writer = ControlledWriter::normal();
    stats.serialize(&mut writer).unwrap();
    writer.calls
}

#[test]
fn buffered_serializer_handles_short_writes_and_interrupted_writes_without_flushing() {
    let values = (0..1025)
        .map(|index| {
            if index % 3 == 0 {
                0
            } else if index % 3 == 1 {
                1
            } else {
                u64::MAX
            }
        })
        .collect::<Vec<_>>();
    let stats = stats_for(&values);
    let mut expected = Vec::new();
    serialize_original(&stats, &values, &mut expected).unwrap();

    let mut short_writer = ControlledWriter::normal();
    short_writer.short_limit = Some(3);
    serialize_current(&stats, &values, &mut short_writer).unwrap();
    assert_eq!(short_writer.bytes, expected);
    assert_eq!(short_writer.flushes, 0);

    let mut interrupted_writer = ControlledWriter::normal();
    interrupted_writer.interrupt_once = true;
    serialize_current(&stats, &values, &mut interrupted_writer).unwrap();
    assert_eq!(interrupted_writer.bytes, expected);
    assert_eq!(interrupted_writer.flushes, 0);
    let mut payload_interrupted_writer = ControlledWriter::normal();
    payload_interrupted_writer.interrupt_on_call = Some(stats_write_calls(&stats) + 1);
    serialize_current(&stats, &values, &mut payload_interrupted_writer).unwrap();
    assert_eq!(payload_interrupted_writer.bytes, expected);
    assert_eq!(payload_interrupted_writer.flushes, 0);
}

#[test]
fn buffered_serializer_propagates_write_failures_without_retrying_on_drop() {
    for length in [1024, 1025] {
        let values = (0..length)
            .map(|index| {
                if index % 3 == 0 {
                    0
                } else if index % 3 == 1 {
                    1
                } else {
                    u64::MAX
                }
            })
            .collect::<Vec<_>>();
        let stats = stats_for(&values);
        let first_payload_call = stats_write_calls(&stats) + 1;

        for (failure, kind) in [
            (Failure::Permanent, ErrorKind::BrokenPipe),
            (Failure::WriteZero, ErrorKind::WriteZero),
        ] {
            let mut writer = ControlledWriter::failing_on(first_payload_call, failure);
            let error = serialize_current(&stats, &values, &mut writer).unwrap_err();
            assert_eq!(error.kind(), kind);
            assert!(writer.failed);
            assert_eq!(writer.calls_after_failure, 0);
            assert_eq!(writer.flushes, 0);
        }
    }
}
