"""Tests for ModelBlueprint schema and related models."""

from datetime import datetime

import pytest
from astro_backend_service.models.fund_model import (
    CellRelationship,
    CellType,
    CrossSheetDependency,
    FormulaType,
    ModelBlueprint,
    RowPattern,
    SheetSpec,
)


class TestCellType:
    """Test CellType enum."""

    def test_enum_values(self):
        """Test all enum values exist."""
        assert CellType.INPUT == "input"
        assert CellType.CALCULATED == "calculated"
        assert CellType.LABEL == "label"
        assert CellType.EMPTY == "empty"


class TestFormulaType:
    """Test FormulaType enum."""

    def test_enum_values(self):
        """Test all formula type values exist."""
        assert FormulaType.DIRECT_REF == "direct_reference"
        assert FormulaType.ARITHMETIC == "arithmetic"
        assert FormulaType.CONDITIONAL == "conditional"
        assert FormulaType.CUMULATIVE == "cumulative"
        assert FormulaType.TIME_SERIES == "time_series"
        assert FormulaType.LOOKUP == "lookup"
        assert FormulaType.WATERFALL == "waterfall"
        assert FormulaType.CUSTOM == "custom"


class TestCellRelationship:
    """Test CellRelationship model."""

    def test_minimal_instantiation(self):
        """Test creating CellRelationship with required fields only."""
        cell = CellRelationship(
            sheet="Cash Flows",
            row=5,
            col=3,
            row_label="Revenue",
            col_label="Q1 2024",
            cell_type=CellType.CALCULATED,
        )
        assert cell.sheet == "Cash Flows"
        assert cell.row == 5
        assert cell.col == 3
        assert cell.cell_type == CellType.CALCULATED
        assert cell.formula_type is None
        assert cell.formula_template is None
        assert cell.depends_on == []
        assert cell.confidence == 1.0
        assert cell.tolerance == 0.01

    def test_full_instantiation(self):
        """Test creating CellRelationship with all fields."""
        cell = CellRelationship(
            sheet="Cash Flows",
            row=5,
            col=3,
            row_label="Revenue",
            col_label="Q1 2024",
            cell_type=CellType.CALCULATED,
            formula_type=FormulaType.TIME_SERIES,
            formula_template="={prior_col}{row}*(1+Assumptions!$B$3)",
            formula_description="Prior period revenue times 1 plus growth rate",
            depends_on=["Cash Flows!Revenue", "Assumptions!Growth_Rate"],
            expected_value=1250000.0,
            tolerance=0.005,
            expert_notes="Growth rate varies by vintage year",
            confidence=0.95,
        )
        assert cell.formula_type == FormulaType.TIME_SERIES
        assert "prior_col" in cell.formula_template
        assert len(cell.depends_on) == 2
        assert cell.expected_value == 1250000.0

    def test_json_serialization(self):
        """Test JSON round-trip."""
        cell = CellRelationship(
            sheet="Fees",
            row=3,
            col=4,
            row_label="Management Fee",
            col_label="Q2 2024",
            cell_type=CellType.CALCULATED,
            formula_type=FormulaType.ARITHMETIC,
        )
        json_str = cell.model_dump_json()
        restored = CellRelationship.model_validate_json(json_str)
        assert restored == cell


class TestRowPattern:
    """Test RowPattern model."""

    def test_minimal_instantiation(self):
        """Test creating RowPattern with required fields only."""
        pattern = RowPattern(
            sheet="Cash Flows",
            row=5,
            row_label="Revenue",
            pattern_type=FormulaType.TIME_SERIES,
            formula_template="={prior_col}{row}*(1+Assumptions!$B$3)",
            first_data_col=3,
            last_data_col=50,
        )
        assert pattern.sheet == "Cash Flows"
        assert pattern.row == 5
        assert pattern.first_data_col == 3
        assert pattern.last_data_col == 50
        assert pattern.seed_col is None
        assert pattern.exceptions == {}

    def test_with_exceptions(self):
        """Test RowPattern with column-specific exceptions."""
        pattern = RowPattern(
            sheet="Cash Flows",
            row=5,
            row_label="Revenue",
            pattern_type=FormulaType.TIME_SERIES,
            formula_template="={prior_col}{row}*(1+Assumptions!$B$3)",
            first_data_col=3,
            last_data_col=50,
            seed_col=2,
            exceptions={
                3: "=Assumptions!$B$2",  # First data col uses initial value
                25: "={prior_col}{row}*(1+Assumptions!$B$4)",  # Mid-point rate change
            },
        )
        assert pattern.seed_col == 2
        assert len(pattern.exceptions) == 2
        assert 3 in pattern.exceptions


class TestSheetSpec:
    """Test SheetSpec model."""

    def test_minimal_instantiation(self):
        """Test creating SheetSpec with required fields only."""
        sheet = SheetSpec(
            name="Cash Flows",
            purpose="Investment cash flows by quarter",
            total_rows=20,
            total_cols=50,
        )
        assert sheet.name == "Cash Flows"
        assert sheet.header_rows == 1  # default
        assert sheet.label_cols == 1  # default
        assert sheet.time_axis == "columns"  # default
        assert sheet.input_rows == []
        assert sheet.calculated_rows == []
        assert sheet.row_patterns == []

    def test_full_instantiation(self):
        """Test creating SheetSpec with all fields."""
        pattern = RowPattern(
            sheet="Cash Flows",
            row=5,
            row_label="Revenue",
            pattern_type=FormulaType.TIME_SERIES,
            formula_template="={prior_col}{row}*(1+Assumptions!$B$3)",
            first_data_col=3,
            last_data_col=50,
        )
        override = CellRelationship(
            sheet="Cash Flows",
            row=10,
            col=3,
            row_label="Special Item",
            col_label="Q1 2024",
            cell_type=CellType.CALCULATED,
            formula_type=FormulaType.CONDITIONAL,
            formula_template="=IF(B10>0, B10*0.2, 0)",
        )
        sheet = SheetSpec(
            name="Cash Flows",
            purpose="Investment cash flows by quarter",
            header_rows=2,
            label_cols=2,
            total_rows=20,
            total_cols=50,
            time_axis="columns",
            time_labels=["Q1 2024", "Q2 2024", "Q3 2024", "Q4 2024"],
            input_rows=[3, 4],
            calculated_rows=[5, 6, 7, 8, 9, 10],
            row_labels={3: "Initial Investment", 4: "Growth Rate", 5: "Revenue"},
            row_patterns=[pattern],
            cell_overrides=[override],
            sections=[
                {"name": "Inputs", "rows": [3, 4]},
                {"name": "Calculations", "rows": [5, 6, 7, 8, 9, 10]},
            ],
        )
        assert sheet.header_rows == 2
        assert len(sheet.time_labels) == 4
        assert len(sheet.row_patterns) == 1
        assert len(sheet.cell_overrides) == 1
        assert len(sheet.sections) == 2


class TestCrossSheetDependency:
    """Test CrossSheetDependency model."""

    def test_instantiation(self):
        """Test creating CrossSheetDependency."""
        dep = CrossSheetDependency(
            source_sheet="Cash Flows",
            source_row_label="Total Cash Flow",
            target_sheet="Distributions",
            target_row_label="Available for Distribution",
            relationship="Distributions.Available = CashFlows.Total - Fees.Management",
        )
        assert dep.source_sheet == "Cash Flows"
        assert dep.target_sheet == "Distributions"


class TestModelBlueprint:
    """Test ModelBlueprint model."""

    @pytest.fixture
    def sample_blueprint(self):
        """Create a sample blueprint for testing."""
        assumptions_sheet = SheetSpec(
            name="Assumptions",
            purpose="Model input assumptions",
            total_rows=10,
            total_cols=2,
            input_rows=[3, 4, 5],
            calculated_rows=[],
        )
        cash_flows_sheet = SheetSpec(
            name="Cash Flows",
            purpose="Investment cash flows by quarter",
            total_rows=15,
            total_cols=50,
            input_rows=[3],
            calculated_rows=[5, 6, 7],
            row_patterns=[
                RowPattern(
                    sheet="Cash Flows",
                    row=5,
                    row_label="Revenue",
                    pattern_type=FormulaType.TIME_SERIES,
                    formula_template="={prior_col}{row}*(1+Assumptions!$B$3)",
                    first_data_col=3,
                    last_data_col=50,
                    seed_col=2,
                )
            ],
        )
        return ModelBlueprint(
            id="fund_model_2024_q1",
            name="Fund Model Q1 2024",
            description="Quarterly fund model for testing",
            sheets=[assumptions_sheet, cash_flows_sheet],
            calculation_order=["Assumptions", "Cash Flows"],
            cross_sheet_deps=[
                CrossSheetDependency(
                    source_sheet="Assumptions",
                    source_row_label="Growth Rate",
                    target_sheet="Cash Flows",
                    target_row_label="Revenue",
                    relationship="Cash Flows uses Assumptions.Growth_Rate for revenue projection",
                )
            ],
            total_calculated_cells=150,
            confirmed_cells=140,
            inferred_cells=5,
        )

    def test_minimal_instantiation(self):
        """Test creating ModelBlueprint with required fields only."""
        blueprint = ModelBlueprint(
            id="test_blueprint",
            name="Test Blueprint",
            description="A test blueprint",
            sheets=[],
            calculation_order=[],
        )
        assert blueprint.id == "test_blueprint"
        assert blueprint.version == "1.0"
        assert blueprint.sheets == []
        assert blueprint.cross_sheet_deps == []
        assert blueprint.completeness == 0.0

    def test_completeness_calculation(self, sample_blueprint):
        """Test completeness computed property."""
        # 140 confirmed + 5 inferred = 145 out of 150
        expected_completeness = 145 / 150
        assert abs(sample_blueprint.completeness - expected_completeness) < 0.001

    def test_is_complete_property(self, sample_blueprint):
        """Test is_complete computed property."""
        # 145/150 < 1.0, so not complete
        assert sample_blueprint.is_complete is False

        # Create a complete blueprint
        complete = ModelBlueprint(
            id="complete",
            name="Complete",
            description="Complete blueprint",
            sheets=[],
            calculation_order=[],
            total_calculated_cells=100,
            confirmed_cells=100,
            inferred_cells=0,
        )
        assert complete.is_complete is True

    def test_get_sheet(self, sample_blueprint):
        """Test get_sheet helper method."""
        sheet = sample_blueprint.get_sheet("Cash Flows")
        assert sheet is not None
        assert sheet.name == "Cash Flows"

        missing = sample_blueprint.get_sheet("NonExistent")
        assert missing is None

    def test_get_pattern_for_row(self, sample_blueprint):
        """Test get_pattern_for_row helper method."""
        pattern = sample_blueprint.get_pattern_for_row("Cash Flows", 5)
        assert pattern is not None
        assert pattern.row_label == "Revenue"

        # Non-existent row
        missing = sample_blueprint.get_pattern_for_row("Cash Flows", 999)
        assert missing is None

        # Non-existent sheet
        missing = sample_blueprint.get_pattern_for_row("NonExistent", 5)
        assert missing is None

    def test_json_serialization(self, sample_blueprint):
        """Test JSON round-trip."""
        json_str = sample_blueprint.model_dump_json()
        restored = ModelBlueprint.model_validate_json(json_str)
        assert restored.id == sample_blueprint.id
        assert restored.name == sample_blueprint.name
        assert len(restored.sheets) == len(sample_blueprint.sheets)
        assert restored.completeness == sample_blueprint.completeness

    def test_with_datetime(self):
        """Test blueprint with datetime field."""
        now = datetime.now()
        blueprint = ModelBlueprint(
            id="dated",
            name="Dated Blueprint",
            description="Blueprint with timestamp",
            sheets=[],
            calculation_order=[],
            created_at=now,
            expert_id="expert_123",
            interview_run_id="run_456",
        )
        assert blueprint.created_at == now
        assert blueprint.expert_id == "expert_123"

    def test_validation_rules(self):
        """Test blueprint with validation rules."""
        blueprint = ModelBlueprint(
            id="validated",
            name="Validated Blueprint",
            description="Blueprint with validation rules",
            sheets=[],
            calculation_order=[],
            validation_rules=[
                {
                    "type": "balance_check",
                    "rule": "total_distributions <= total_cash_inflows",
                    "severity": "error",
                },
                {
                    "type": "positivity_check",
                    "rule": "management_fees >= 0",
                    "severity": "warning",
                },
            ],
        )
        assert len(blueprint.validation_rules) == 2
        assert blueprint.validation_rules[0]["type"] == "balance_check"


class TestRealWorldScenario:
    """Test with a more realistic fund model structure."""

    def test_pe_fund_model_structure(self):
        """Test creating a blueprint for a typical PE fund model."""
        # Assumptions sheet - inputs only
        assumptions = SheetSpec(
            name="Assumptions",
            purpose="Fund parameters and assumptions",
            total_rows=15,
            total_cols=2,
            input_rows=[3, 4, 5, 6, 7, 8, 9, 10],
            calculated_rows=[],
            row_labels={
                3: "Fund Size",
                4: "Management Fee Rate",
                5: "Carried Interest Rate",
                6: "Hurdle Rate",
                7: "Investment Period (Years)",
                8: "Fund Life (Years)",
                9: "Expected IRR",
                10: "Expected MOIC",
            },
        )

        # Cash Flows sheet - mix of inputs and calculated
        cash_flows = SheetSpec(
            name="Cash Flows",
            purpose="Investment cash flows by quarter",
            total_rows=20,
            total_cols=50,
            header_rows=1,
            label_cols=1,
            input_rows=[3, 4],  # Capital calls, distributions (inputs)
            calculated_rows=[6, 7, 8, 9, 10],  # Net cash flow, cumulative, etc.
            time_labels=[f"Q{q} {2024 + (i // 4)}" for i, q in enumerate([1, 2, 3, 4] * 12)],
            row_patterns=[
                RowPattern(
                    sheet="Cash Flows",
                    row=6,
                    row_label="Net Cash Flow",
                    pattern_type=FormulaType.ARITHMETIC,
                    formula_template="={col_letter}4-{col_letter}3",  # Distributions - Calls
                    first_data_col=2,
                    last_data_col=50,
                ),
                RowPattern(
                    sheet="Cash Flows",
                    row=7,
                    row_label="Cumulative Net CF",
                    pattern_type=FormulaType.CUMULATIVE,
                    formula_template="={prior_col}7+{col_letter}6",
                    first_data_col=3,
                    last_data_col=50,
                    seed_col=2,
                ),
            ],
            row_labels={
                3: "Capital Calls",
                4: "Distributions",
                6: "Net Cash Flow",
                7: "Cumulative Net CF",
                8: "NAV",
                9: "DPI",
                10: "TVPI",
            },
        )

        # Fees sheet - calculated from Assumptions and Cash Flows
        fees = SheetSpec(
            name="Fees",
            purpose="Management and incentive fee calculations",
            total_rows=10,
            total_cols=50,
            calculated_rows=[3, 4, 5],
            row_patterns=[
                RowPattern(
                    sheet="Fees",
                    row=3,
                    row_label="Management Fee",
                    pattern_type=FormulaType.ARITHMETIC,
                    formula_template="='Cash Flows'!{col_letter}8*Assumptions!$B$4",  # NAV * fee rate
                    first_data_col=2,
                    last_data_col=50,
                ),
            ],
        )

        # Create the full blueprint
        blueprint = ModelBlueprint(
            id="pe_fund_model_v1",
            name="PE Fund Model",
            description="Private equity fund model with fees and distributions",
            version="1.0",
            sheets=[assumptions, cash_flows, fees],
            calculation_order=["Assumptions", "Cash Flows", "Fees"],
            cross_sheet_deps=[
                CrossSheetDependency(
                    source_sheet="Cash Flows",
                    source_row_label="NAV",
                    target_sheet="Fees",
                    target_row_label="Management Fee",
                    relationship="Management Fee = NAV × Management Fee Rate",
                ),
                CrossSheetDependency(
                    source_sheet="Assumptions",
                    source_row_label="Management Fee Rate",
                    target_sheet="Fees",
                    target_row_label="Management Fee",
                    relationship="Fee rate from Assumptions drives Fees calculation",
                ),
            ],
            validation_rules=[
                {
                    "type": "positivity",
                    "rule": "management_fee >= 0",
                    "description": "Management fees should never be negative",
                },
                {
                    "type": "upper_bound",
                    "rule": "dpi <= tvpi",
                    "description": "DPI should not exceed TVPI",
                },
            ],
            total_calculated_cells=250,
            confirmed_cells=240,
            inferred_cells=8,
        )

        # Verify structure
        assert len(blueprint.sheets) == 3
        assert blueprint.calculation_order == ["Assumptions", "Cash Flows", "Fees"]
        assert len(blueprint.cross_sheet_deps) == 2

        # Verify completeness
        assert blueprint.completeness == 248 / 250
        assert blueprint.is_complete is False

        # Verify sheet retrieval
        cf_sheet = blueprint.get_sheet("Cash Flows")
        assert cf_sheet is not None
        assert len(cf_sheet.row_patterns) == 2

        # Verify pattern retrieval
        net_cf_pattern = blueprint.get_pattern_for_row("Cash Flows", 6)
        assert net_cf_pattern is not None
        assert net_cf_pattern.pattern_type == FormulaType.ARITHMETIC

        # Test JSON serialization
        json_str = blueprint.model_dump_json()
        restored = ModelBlueprint.model_validate_json(json_str)
        assert restored.id == blueprint.id
        assert len(restored.sheets) == 3
