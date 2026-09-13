use std::error::Error;
use std::time::Instant;

use serde_json::{json, Value};
use tantivy_columnar::{
    merge_columnar, Cardinality, ColumnType, ColumnarReader, ColumnarWriter, DynamicColumn,
    StackMergeOrder,
};

const SEGMENTS: u32 = 8;
const VALUES_PER_DOC: u32 = 384;
const WARMUPS: u32 = 1;
const MEASURED_MERGES: u32 = 12;

fn fixture_value(segment: u32, doc: u32, value: u32, docs_per_segment: u32) -> f64 {
    let row = segment
        .checked_mul(docs_per_segment)
        .and_then(|n| n.checked_add(doc))
        .expect("fixture row overflow");
    // Same numeric distribution as the full load runner's vector_for.
    (((u64::from(row) + 1) * 31 + u64::from(value) * 17) % 1000) as f64 / 1000.0
}

fn build_segments(docs_per_segment: u32) -> Result<Vec<ColumnarReader>, Box<dyn Error>> {
    let mut readers = Vec::with_capacity(SEGMENTS as usize);
    for segment in 0..SEGMENTS {
        let mut writer = ColumnarWriter::default();
        writer.record_column_type("numbers", ColumnType::F64, false);
        for doc in 0..docs_per_segment {
            for value in 0..VALUES_PER_DOC {
                writer.record_numerical(doc, "numbers", fixture_value(segment, doc, value, docs_per_segment));
            }
        }
        let mut bytes = Vec::new();
        writer.serialize(docs_per_segment, None, &mut bytes)?;
        readers.push(ColumnarReader::open(bytes)?);
    }
    Ok(readers)
}

fn validate(
    reader: &ColumnarReader,
    docs_per_segment: u32,
) -> Result<(u64, u64), Box<dyn Error>> {
    let expected_rows = SEGMENTS.checked_mul(docs_per_segment).expect("row count overflow");
    assert_eq!(reader.num_rows(), expected_rows);
    let columns = reader.read_columns("numbers")?;
    assert_eq!(columns.len(), 1);
    let DynamicColumn::F64(column) = columns[0].open()? else {
        panic!("numbers must remain an F64 column");
    };
    assert_eq!(column.get_cardinality(), Cardinality::Multivalued);
    assert_eq!(column.num_docs(), expected_rows);
    let mut values_checked = 0u64;
    for row in 0..expected_rows {
        let segment = row / docs_per_segment;
        let doc = row % docs_per_segment;
        let values: Vec<f64> = column.values_for_doc(row).collect();
        assert_eq!(values.len(), VALUES_PER_DOC as usize);
        for (value, actual) in values.into_iter().enumerate() {
            let expected = fixture_value(segment, doc, value as u32, docs_per_segment);
            assert_eq!(actual.to_bits(), expected.to_bits(), "row {row}, value {value}");
            values_checked = values_checked.checked_add(1).expect("validation count overflow");
        }
    }
    Ok((u64::from(expected_rows), values_checked))
}

fn run_condition(name: &str, docs_per_segment: u32) -> Result<Value, Box<dyn Error>> {
    let total_rows = SEGMENTS.checked_mul(docs_per_segment).expect("row count overflow");
    let total_values = total_rows
        .checked_mul(VALUES_PER_DOC)
        .expect("value count overflow");
    let readers = build_segments(docs_per_segment)?;
    let reader_refs: Vec<&ColumnarReader> = readers.iter().collect();
    let mut canonical_bytes: Option<Vec<u8>> = None;
    let mut milliseconds = Vec::with_capacity(MEASURED_MERGES as usize);
    let mut rows_checked = 0u64;
    let mut values_checked = 0u64;
    for repetition in 0..WARMUPS + MEASURED_MERGES {
        let merge_order = StackMergeOrder::stack(&reader_refs).into();
        let mut output = Vec::new();
        let started = Instant::now();
        merge_columnar(&reader_refs, &[], merge_order, &mut output)?;
        let elapsed_ms = started.elapsed().as_secs_f64() * 1_000.0;
        let (rows, values) = validate(&ColumnarReader::open(output.clone())?, docs_per_segment)?;
        rows_checked = rows_checked.checked_add(rows).expect("row validation count overflow");
        values_checked = values_checked.checked_add(values).expect("value validation count overflow");
        if let Some(expected) = &canonical_bytes {
            assert_eq!(&output, expected, "encoded bytes changed at repetition {repetition}");
        } else {
            canonical_bytes = Some(output);
        }
        if repetition >= WARMUPS {
            milliseconds.push(elapsed_ms);
        }
    }
    let output_bytes = canonical_bytes.expect("at least one merge").len();
    Ok(json!({
        "condition": name,
        "inputs": { "segments": SEGMENTS, "docs_per_segment": docs_per_segment, "values_per_doc": VALUES_PER_DOC, "total_rows": total_rows, "total_values": total_values },
        "per_repetition_milliseconds": milliseconds,
        "output_bytes": output_bytes,
        "validation_counts": { "outputs": WARMUPS + MEASURED_MERGES, "rows": rows_checked, "values": values_checked }
    }))
}

fn main() -> Result<(), Box<dyn Error>> {
    let report = json!({
        "diagnostic_only": true,
        "acceptance_established": false,
        "workload": {
            "native_api": "tantivy_columnar::merge_columnar with StackMergeOrder",
            "value_formula": "(((row + 1) * 31 + offset * 17) % 1000) / 1000.0",
            "column": { "name": "numbers", "type": "F64", "cardinality": "Multivalued" },
            "warmups": WARMUPS,
            "measured_merges": MEASURED_MERGES
        },
        "conditions": [
            run_condition("eight_segments_128_docs", 128)?,
            run_condition("eight_segments_2_docs", 2)?
        ]
    });
    println!("{}", serde_json::to_string(&report)?);
    Ok(())
}
