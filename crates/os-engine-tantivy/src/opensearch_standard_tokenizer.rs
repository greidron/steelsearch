use tantivy::tokenizer::{Token, TokenStream, Tokenizer};
use unicode_normalization::char::is_combining_mark;

/// Bounded native equivalent of the OpenSearch standard tokenizer used by the
/// default text mapping. Tantivy's built-in default tokenizer drops pictographs.
#[derive(Clone, Default)]
pub(super) struct OpenSearchStandardTokenizer;

pub(super) struct OpenSearchStandardTokenStream {
    tokens: Vec<Token>,
    next: usize,
}

impl Tokenizer for OpenSearchStandardTokenizer {
    type TokenStream<'a> = OpenSearchStandardTokenStream;

    fn token_stream<'a>(&'a mut self, text: &'a str) -> Self::TokenStream<'a> {
        OpenSearchStandardTokenStream {
            tokens: standard_tokens(text),
            next: 0,
        }
    }
}

impl TokenStream for OpenSearchStandardTokenStream {
    fn advance(&mut self) -> bool {
        if self.next == self.tokens.len() {
            return false;
        }
        self.next += 1;
        true
    }

    fn token(&self) -> &Token {
        &self.tokens[self.next - 1]
    }

    fn token_mut(&mut self) -> &mut Token {
        &mut self.tokens[self.next - 1]
    }
}

const LUCENE_STANDARD_MAX_TOKEN_UTF16_LENGTH: usize = 255;

fn standard_tokens(text: &str) -> Vec<Token> {
    let characters = text.char_indices().collect::<Vec<_>>();
    let mut tokens = Vec::new();
    let mut cursor = 0;
    while cursor < characters.len() {
        let Some((end, chunk_at_utf16_limit)) = token_end(&characters, cursor) else {
            cursor += 1;
            continue;
        };
        if chunk_at_utf16_limit {
            push_word_chunks(text, &characters, cursor, end, &mut tokens);
        } else {
            push_token(text, &characters, cursor, end, &mut tokens);
        }
        cursor = end;
    }
    tokens
}

fn token_end(characters: &[(usize, char)], cursor: usize) -> Option<(usize, bool)> {
    let character = characters[cursor].1;
    if is_ideographic(character) || is_hiragana(character) {
        return Some((cursor + 1, false));
    }
    if is_katakana(character) {
        return Some((consume_while(characters, cursor, is_katakana), false));
    }
    if is_hangul(character) {
        return Some((consume_while(characters, cursor, is_hangul), false));
    }
    if is_southeast_asian(character) {
        return Some((consume_while(characters, cursor, is_southeast_asian), false));
    }
    if is_emoji_start(characters, cursor) {
        return Some((emoji_end(characters, cursor), false));
    }
    if is_generic_alphanumeric(character) {
        let mut end = cursor + 1;
        while end < characters.len() {
            let next = characters[end].1;
            if is_generic_alphanumeric(next) || is_combining_mark(next) {
                end += 1;
            } else if is_mid_letter_apostrophe(characters, end) {
                end += 1;
            } else {
                break;
            }
        }
        return Some((end, true));
    }
    None
}

fn push_word_chunks(
    text: &str,
    characters: &[(usize, char)],
    start: usize,
    end: usize,
    tokens: &mut Vec<Token>,
) {
    let mut chunk_start = start;
    let mut utf16_length = 0;
    for cursor in start..end {
        let character_length = characters[cursor].1.len_utf16();
        if utf16_length > 0
            && utf16_length + character_length > LUCENE_STANDARD_MAX_TOKEN_UTF16_LENGTH
        {
            push_token(text, characters, chunk_start, cursor, tokens);
            chunk_start = cursor;
            utf16_length = 0;
        }
        utf16_length += character_length;
    }
    push_token(text, characters, chunk_start, end, tokens);
}

fn push_token(
    text: &str,
    characters: &[(usize, char)],
    start: usize,
    end: usize,
    tokens: &mut Vec<Token>,
) {
    let start_offset = characters[start].0;
    let end_offset = characters
        .get(end)
        .map(|(offset, _)| *offset)
        .unwrap_or(text.len());
    let mut token = Token::default();
    token.offset_from = start_offset;
    token.offset_to = end_offset;
    token.position = tokens.len();
    token.position_length = 1;
    token.text.push_str(&text[start_offset..end_offset]);
    tokens.push(token);
}

fn consume_while(
    characters: &[(usize, char)],
    mut cursor: usize,
    predicate: impl Fn(char) -> bool,
) -> usize {
    while cursor < characters.len() && predicate(characters[cursor].1) {
        cursor += 1;
    }
    cursor
}

fn is_mid_letter_apostrophe(characters: &[(usize, char)], cursor: usize) -> bool {
    matches!(characters[cursor].1, '\'' | '\u{2019}')
        && cursor > 0
        && cursor + 1 < characters.len()
        && is_generic_alphanumeric(characters[cursor - 1].1)
        && is_generic_alphanumeric(characters[cursor + 1].1)
}

fn is_generic_alphanumeric(character: char) -> bool {
    character.is_alphanumeric()
        && !is_ideographic(character)
        && !is_hiragana(character)
        && !is_katakana(character)
        && !is_hangul(character)
        && !is_southeast_asian(character)
}

fn is_ideographic(character: char) -> bool {
    matches!(character as u32,
        0x3006 | 0x3007 | 0x3400..=0x4DBF | 0x4E00..=0x9FFF | 0xF900..=0xFAFF |
        0x20000..=0x2A6DF | 0x2A700..=0x2B81F | 0x2B820..=0x2CEAF | 0x2CEB0..=0x2EBEF |
        0x30000..=0x3134F | 0x31350..=0x323AF)
}

fn is_hiragana(character: char) -> bool {
    matches!(character as u32, 0x3041..=0x3096 | 0x309D..=0x309F)
}

fn is_katakana(character: char) -> bool {
    matches!(character as u32,
        0x30A1..=0x30FA | 0x30FC..=0x30FF | 0x31A0..=0x31BF | 0x31F0..=0x31FF |
        0xFF66..=0xFF9D)
}

fn is_hangul(character: char) -> bool {
    matches!(character as u32,
        0x1100..=0x11FF | 0x3130..=0x318F | 0xA960..=0xA97F | 0xAC00..=0xD7AF)
}

fn is_southeast_asian(character: char) -> bool {
    matches!(character as u32, 0x0E00..=0x0E7F | 0x0E80..=0x0EFF | 0x1000..=0x109F | 0x1780..=0x17FF)
}

fn is_emoji_start(characters: &[(usize, char)], cursor: usize) -> bool {
    is_regional_indicator(characters[cursor].1)
        || is_extended_pictographic(characters[cursor].1)
        || is_keycap_start(characters, cursor)
}

fn emoji_end(characters: &[(usize, char)], mut cursor: usize) -> usize {
    if is_regional_indicator(characters[cursor].1) {
        cursor += 1;
        if cursor < characters.len() && is_regional_indicator(characters[cursor].1) {
            cursor += 1;
        }
        return cursor;
    }
    if is_keycap_start(characters, cursor) {
        cursor += 1;
        if cursor < characters.len() && is_variation_selector(characters[cursor].1) {
            cursor += 1;
        }
        return cursor + 1;
    }
    cursor = consume_emoji_component(characters, cursor);
    while cursor + 1 < characters.len()
        && characters[cursor].1 == '\u{200D}'
        && (is_extended_pictographic(characters[cursor + 1].1)
            || is_regional_indicator(characters[cursor + 1].1))
    {
        cursor = consume_emoji_component(characters, cursor + 1);
    }
    cursor
}

fn consume_emoji_component(characters: &[(usize, char)], mut cursor: usize) -> usize {
    cursor += 1;
    while cursor < characters.len()
        && (is_variation_selector(characters[cursor].1) || is_emoji_modifier(characters[cursor].1))
    {
        cursor += 1;
    }
    cursor
}

fn is_keycap_start(characters: &[(usize, char)], cursor: usize) -> bool {
    matches!(characters[cursor].1, '#' | '*' | '0'..='9')
        && matches!(
            characters.get(cursor + 1).map(|(_, character)| *character),
            Some('\u{20E3}') | Some('\u{FE0F}')
        )
        && matches!(
            characters.get(cursor + 2).map(|(_, character)| *character),
            Some('\u{20E3}')
        )
}

fn is_variation_selector(character: char) -> bool {
    matches!(character as u32, 0xFE0E | 0xFE0F)
}

fn is_emoji_modifier(character: char) -> bool {
    matches!(character as u32, 0x1F3FB..=0x1F3FF)
}

fn is_regional_indicator(character: char) -> bool {
    matches!(character as u32, 0x1F1E6..=0x1F1FF)
}

fn is_extended_pictographic(character: char) -> bool {
    matches!(character as u32,
        0x00A9 | 0x00AE | 0x203C | 0x2049 | 0x2122 | 0x2139 | 0x2194..=0x2199 |
        0x21A9..=0x21AA | 0x231A..=0x231B | 0x2328 | 0x23CF | 0x23E9..=0x23F3 |
        0x23F8..=0x23FA | 0x24C2 | 0x25AA..=0x25AB | 0x25B6 | 0x25C0 |
        0x25FB..=0x25FE | 0x2600..=0x27BF | 0x2934..=0x2935 | 0x2B05..=0x2B07 |
        0x2B1B..=0x2B1C | 0x2B50 | 0x2B55 | 0x3030 | 0x303D | 0x3297 | 0x3299 |
        0x1F000..=0x1FAFF)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn preserves_combining_marks_and_pictographs_with_positions() {
        let mut tokenizer = OpenSearchStandardTokenizer;
        let mut stream = tokenizer.token_stream("cafe\u{301} \u{1F600} beta");
        let tokens = std::iter::from_fn(|| stream.advance().then(|| stream.token().clone()))
            .collect::<Vec<_>>();
        assert_eq!(
            tokens
                .iter()
                .map(|token| (
                    token.text.as_str(),
                    token.position,
                    token.offset_from,
                    token.offset_to
                ))
                .collect::<Vec<_>>(),
            vec![
                ("cafe\u{301}", 0, 0, 6),
                ("\u{1F600}", 1, 7, 11),
                ("beta", 2, 12, 16)
            ],
        );
    }

    #[test]
    fn matches_pinned_lucene_standard_boundaries() {
        assert_eq!(
            tokens("\u{6F22}\u{5B57} \u{304B}\u{306A} \u{30AB}\u{30BF}\u{30AB}\u{30CA} \u{D55C}\u{AE00}"),
            vec![
                ("\u{6F22}".into(), 0, 0, 3),
                ("\u{5B57}".into(), 1, 3, 6),
                ("\u{304B}".into(), 2, 7, 10),
                ("\u{306A}".into(), 3, 10, 13),
                ("\u{30AB}\u{30BF}\u{30AB}\u{30CA}".into(), 4, 14, 26),
                ("\u{D55C}\u{AE00}".into(), 5, 27, 33),
            ],
        );
        assert_eq!(
            tokens("\u{0E20}\u{0E32}\u{0E29}\u{0E32}\u{0E44}\u{0E17}\u{0E22} \u{1781}\u{17D2}\u{1798}\u{17C2}\u{179A}"),
            vec![
                ("\u{0E20}\u{0E32}\u{0E29}\u{0E32}\u{0E44}\u{0E17}\u{0E22}".into(), 0, 0, 21),
                ("\u{1781}\u{17D2}\u{1798}\u{17C2}\u{179A}".into(), 1, 22, 37),
            ],
        );
        assert_eq!(
            tokens("\u{1F44D}\u{1F3FD} \u{1F469}\u{200D}\u{1F4BB} \u{1F1FA}\u{1F1F8} 1\u{FE0F}\u{20E3}"),
            vec![
                ("\u{1F44D}\u{1F3FD}".into(), 0, 0, 8),
                ("\u{1F469}\u{200D}\u{1F4BB}".into(), 1, 9, 20),
                ("\u{1F1FA}\u{1F1F8}".into(), 2, 21, 29),
                ("1\u{FE0F}\u{20E3}".into(), 3, 30, 37),
            ],
        );
        assert_eq!(
            tokens("can't l\u{2019}esprit rock'n'roll"),
            vec![
                ("can't".into(), 0, 0, 5),
                ("l\u{2019}esprit".into(), 1, 6, 16),
                ("rock'n'roll".into(), 2, 17, 28),
            ],
        );
    }

    #[test]
    fn splits_words_at_lucene_default_utf16_limit() {
        let input = "a".repeat(256);
        let tokens = tokens(&input);
        assert_eq!(tokens.len(), 2);
        assert_eq!(tokens[0], (input[..255].into(), 0, 0, 255));
        assert_eq!(tokens[1], ("a".into(), 1, 255, 256));
    }

    fn tokens(text: &str) -> Vec<(String, usize, usize, usize)> {
        let mut tokenizer = OpenSearchStandardTokenizer;
        let mut stream = tokenizer.token_stream(text);
        std::iter::from_fn(|| stream.advance().then(|| stream.token().clone()))
            .map(|token| {
                (
                    token.text,
                    token.position,
                    token.offset_from,
                    token.offset_to,
                )
            })
            .collect()
    }
}
