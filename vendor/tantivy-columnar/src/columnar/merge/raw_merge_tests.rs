use common::DateTime;

use super::*;
use crate::{ColumnarReader, ColumnarWriter, DynamicColumn, NumericalValue, RowAddr};

fn numerical_columnar(column_type: ColumnType, rows: &[&[NumericalValue]]) -> ColumnarReader {
    let mut writer = ColumnarWriter::default();
    writer.record_column_type("value", column_type, false);
    for (row_id, values) in rows.iter().enumerate() {
        for &value in *values {
            writer.record_numerical(row_id as u32, "value", value);
        }
    }
    let mut bytes = Vec::new();
    writer.serialize(rows.len() as u32, None, &mut bytes).unwrap();
    ColumnarReader::open(bytes).unwrap()
}

fn empty_columnar(num_rows: u32) -> ColumnarReader {
    let mut bytes = Vec::new();
    ColumnarWriter::default()
        .serialize(num_rows, None, &mut bytes)
        .unwrap();
    ColumnarReader::open(bytes).unwrap()
}

fn merged(
    readers: &[&ColumnarReader],
    required: &[(String, ColumnType)],
    order: MergeRowOrder,
    use_raw_u64: bool,
) -> Vec<u8> {
    let mut bytes = Vec::new();
    merge_columnar_impl(readers, required, order, &mut bytes, use_raw_u64).unwrap();
    bytes
}

fn assert_stack_parity(readers: &[&ColumnarReader], required: &[(String, ColumnType)]) -> Vec<u8> {
    let optimized = merged(
        readers,
        required,
        StackMergeOrder::stack(readers).into(),
        true,
    );
    let original = merged(
        readers,
        required,
        StackMergeOrder::stack(readers).into(),
        false,
    );
    assert_eq!(optimized, original);
    optimized
}

fn assert_raw_eligible(
    readers: &[&ColumnarReader],
    required: &[(String, ColumnType)],
    order: &MergeRowOrder,
    category: ColumnTypeCategory,
    expected: bool,
) {
    let grouped = group_columns_for_merge(readers, required, order).unwrap();
    let handle = grouped
        .iter()
        .find(|((_, actual_category), _)| *actual_category == category)
        .map(|(_, handle)| handle)
        .expect("test column should be grouped");
    assert_eq!(handle.open_homogeneous_u64(order).unwrap().is_some(), expected);
}

#[test]
fn raw_stack_matches_original_for_homogeneous_numerics_and_decodes_values() {
    let floats = [
        numerical_columnar(
            ColumnType::F64,
            &[&[NumericalValue::F64(-0.0)], &[NumericalValue::F64(f64::MIN)]],
        ),
        numerical_columnar(
            ColumnType::F64,
            &[&[], &[NumericalValue::F64(0.0), NumericalValue::F64(f64::MAX)]],
        ),
    ];
    let float_refs = [&floats[0], &floats[1]];
    let order: MergeRowOrder = StackMergeOrder::stack(&float_refs).into();
    assert_raw_eligible(&float_refs, &[], &order, ColumnTypeCategory::Numerical, true);
    let merged_floats = ColumnarReader::open(assert_stack_parity(&float_refs, &[])).unwrap();
    let DynamicColumn::F64(column) = merged_floats.read_columns("value").unwrap()[0].open().unwrap() else {
        panic!("merged float column changed type");
    };
    assert_eq!(column.values_for_doc(0).next().unwrap().to_bits(), (-0.0_f64).to_bits());
    assert!(column.values_for_doc(1).next().unwrap().is_sign_negative());
    assert!(column.values_for_doc(2).next().is_none());
    assert_eq!(column.values_for_doc(3).collect::<Vec<_>>(), vec![0.0, f64::MAX]);

    for (column_type, rows) in [
        (
            ColumnType::I64,
            vec![vec![NumericalValue::I64(i64::MIN)], vec![NumericalValue::I64(i64::MAX)]],
        ),
        (
            ColumnType::U64,
            vec![vec![NumericalValue::U64(0)], vec![NumericalValue::U64(u64::MAX)]],
        ),
    ] {
        let left = numerical_columnar(column_type, &[&rows[0]]);
        let right = numerical_columnar(column_type, &[&rows[1]]);
        let readers = [&left, &right];
        let merged_reader = ColumnarReader::open(assert_stack_parity(&readers, &[])).unwrap();
        let column = merged_reader.read_columns("value").unwrap()[0].open().unwrap();
        match column {
            DynamicColumn::I64(column) => assert_eq!(
                column.values_for_doc(0).chain(column.values_for_doc(1)).collect::<Vec<_>>(),
                vec![i64::MIN, i64::MAX],
            ),
            DynamicColumn::U64(column) => assert_eq!(
                column.values_for_doc(0).chain(column.values_for_doc(1)).collect::<Vec<_>>(),
                vec![0, u64::MAX],
            ),
            _ => panic!("merged integer column changed type"),
        }
    }
}

#[test]
fn raw_stack_matches_original_with_missing_empty_and_multivalued_rows() {
    let first = numerical_columnar(
        ColumnType::U64,
        &[&[], &[NumericalValue::U64(3), NumericalValue::U64(1)], &[]],
    );
    let empty = numerical_columnar(ColumnType::U64, &[&[], &[]]);
    let missing = empty_columnar(2);
    let readers = [&first, &empty, &missing];
    let order: MergeRowOrder = StackMergeOrder::stack(&readers).into();
    assert_raw_eligible(&readers, &[], &order, ColumnTypeCategory::Numerical, true);
    let merged_reader = ColumnarReader::open(assert_stack_parity(&readers, &[])).unwrap();
    let DynamicColumn::U64(column) = merged_reader.read_columns("value").unwrap()[0].open().unwrap() else {
        panic!("merged u64 column changed type");
    };
    assert_eq!(column.values_for_doc(0).collect::<Vec<_>>(), Vec::<u64>::new());
    assert_eq!(column.values_for_doc(1).collect::<Vec<_>>(), vec![3, 1]);
    assert_eq!(column.values_for_doc(3).collect::<Vec<_>>(), Vec::<u64>::new());
    assert_eq!(column.values_for_doc(5).collect::<Vec<_>>(), Vec::<u64>::new());
}

#[test]
fn raw_stack_matches_original_for_bool_and_datetime() {
    let mut left_writer = ColumnarWriter::default();
    left_writer.record_bool(0, "bool", false);
    left_writer.record_datetime(1, "date", DateTime::from_timestamp_nanos(i64::MIN));
    let mut left_bytes = Vec::new();
    left_writer.serialize(2, None, &mut left_bytes).unwrap();
    let left = ColumnarReader::open(left_bytes).unwrap();

    let mut right_writer = ColumnarWriter::default();
    right_writer.record_bool(1, "bool", true);
    right_writer.record_datetime(0, "date", DateTime::from_timestamp_nanos(i64::MAX));
    let mut right_bytes = Vec::new();
    right_writer.serialize(2, None, &mut right_bytes).unwrap();
    let right = ColumnarReader::open(right_bytes).unwrap();
    let readers = [&left, &right];
    let order: MergeRowOrder = StackMergeOrder::stack(&readers).into();
    assert_raw_eligible(&readers, &[], &order, ColumnTypeCategory::Bool, true);
    assert_raw_eligible(&readers, &[], &order, ColumnTypeCategory::DateTime, true);
    let merged_reader = ColumnarReader::open(assert_stack_parity(&readers, &[])).unwrap();
    let DynamicColumn::Bool(bool_column) = merged_reader.read_columns("bool").unwrap()[0].open().unwrap() else {
        panic!("merged bool column changed type");
    };
    assert_eq!(bool_column.values_for_doc(0).next(), Some(false));
    assert_eq!(bool_column.values_for_doc(3).next(), Some(true));
    let DynamicColumn::DateTime(date_column) = merged_reader.read_columns("date").unwrap()[0].open().unwrap() else {
        panic!("merged datetime column changed type");
    };
    assert_eq!(
        date_column.values_for_doc(1).next().unwrap().into_timestamp_nanos(),
        i64::MIN,
    );
    assert_eq!(
        date_column.values_for_doc(2).next().unwrap().into_timestamp_nanos(),
        i64::MAX,
    );
}

#[test]
fn raw_merge_falls_back_for_required_coercion_mixed_types_and_shuffle() {
    let left = numerical_columnar(ColumnType::I64, &[&[NumericalValue::I64(1)], &[NumericalValue::I64(2)]]);
    let right = numerical_columnar(ColumnType::I64, &[&[NumericalValue::I64(3)]]);
    let readers = [&left, &right];
    let same_required = [("value".to_string(), ColumnType::I64)];
    let stack: MergeRowOrder = StackMergeOrder::stack(&readers).into();
    assert_raw_eligible(&readers, &same_required, &stack, ColumnTypeCategory::Numerical, true);
    assert_stack_parity(&readers, &same_required);

    let different_required = [("value".to_string(), ColumnType::U64)];
    assert_raw_eligible(&readers, &different_required, &stack, ColumnTypeCategory::Numerical, false);
    assert_stack_parity(&readers, &different_required);

    let mixed = numerical_columnar(ColumnType::U64, &[&[NumericalValue::U64(4)]]);
    let mixed_readers = [&left, &mixed];
    let mixed_stack: MergeRowOrder = StackMergeOrder::stack(&mixed_readers).into();
    assert_raw_eligible(&mixed_readers, &[], &mixed_stack, ColumnTypeCategory::Numerical, false);
    assert_stack_parity(&mixed_readers, &[]);

    let shuffled = MergeRowOrder::Shuffled(ShuffleMergeOrder::for_test(
        &[left.num_rows(), right.num_rows()],
        vec![
            RowAddr { segment_ord: 1, row_id: 0 },
            RowAddr { segment_ord: 0, row_id: 0 },
        ],
    ));
    assert_raw_eligible(&readers, &[], &shuffled, ColumnTypeCategory::Numerical, false);
    let optimized = merged(&readers, &[], shuffled, true);
    let original = merged(
        &readers,
        &[],
        MergeRowOrder::Shuffled(ShuffleMergeOrder::for_test(
            &[left.num_rows(), right.num_rows()],
            vec![
                RowAddr { segment_ord: 1, row_id: 0 },
                RowAddr { segment_ord: 0, row_id: 0 },
            ],
        )),
        false,
    );
    assert_eq!(optimized, original);
}

#[test]
fn raw_merge_preserves_nonfinite_bits_and_required_type_errors() {
    let values = [f64::NEG_INFINITY, f64::INFINITY, f64::from_bits(0x7ff8_0000_0000_0042)];
    let first = numerical_columnar(ColumnType::F64, &[&[NumericalValue::F64(values[0])]]);
    let second = numerical_columnar(ColumnType::F64,
        &[&[NumericalValue::F64(values[1]), NumericalValue::F64(values[2])]]);
    let readers = [&first, &second];
    let result = ColumnarReader::open(assert_stack_parity(&readers, &[])).unwrap();
    let DynamicColumn::F64(column) = result.read_columns("value").unwrap()[0].open().unwrap() else {
        panic!("nonfinite column changed type");
    };
    let actual: Vec<_> = column.values.iter().map(f64::to_bits).collect();
    assert_eq!(actual, values.into_iter().map(f64::to_bits).collect::<Vec<_>>());

    let negative = numerical_columnar(ColumnType::I64, &[&[NumericalValue::I64(-1)]]);
    let readers = [&negative];
    let required = [("value".to_owned(), ColumnType::U64)];
    let mut errors = Vec::new();
    for use_raw in [false, true] {
        let error = merge_columnar_impl(&readers, &required,
            StackMergeOrder::stack(&readers).into(), &mut Vec::new(), use_raw).unwrap_err();
        errors.push(error.kind());
    }
    assert_eq!(errors[0], errors[1]);
}

#[test]
fn raw_merge_preserves_all_empty_and_missing_required_columns() {
    let empty = numerical_columnar(ColumnType::U64, &[&[], &[]]);
    let missing = empty_columnar(3);
    let readers = [&empty, &missing];
    assert_stack_parity(&readers, &[]);
    assert_stack_parity(&readers, &[("value".to_owned(), ColumnType::U64)]);
}
