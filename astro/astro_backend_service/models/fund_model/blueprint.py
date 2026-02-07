"""
Model Blueprint schema for fund model reverse-engineering.

The Blueprint is the central artifact produced by Phase 1 (learning) and consumed
by Phase 2 (reconstruction). It captures the complete structure and logic of a
fund model in a format that enables autonomous reconstruction.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, computed_field


class CellType(str, Enum):
    """Classification of a cell's role in the model."""

    INPUT = "input"  # Hardcoded value, provided by user
    CALCULATED = "calculated"  # Derived from formula
    LABEL = "label"  # Row/column header, not data
    EMPTY = "empty"  # Intentionally blank


class FormulaType(str, Enum):
    """Classification of formula patterns found in fund models."""

    DIRECT_REF = "direct_reference"  # =OtherSheet!B5
    ARITHMETIC = "arithmetic"  # =B5 * C3
    CONDITIONAL = "conditional"  # =IF(B5>0, B5*0.2, 0)
    CUMULATIVE = "cumulative"  # =SUM(B5:B20)
    TIME_SERIES = "time_series"  # =D5*(1+$B$3) — prior period × growth
    LOOKUP = "lookup"  # =VLOOKUP(...) or INDEX/MATCH
    WATERFALL = "waterfall"  # Multi-tier conditional (hurdle rates)
    CUSTOM = "custom"  # Complex logic requiring expert description


class CellRelationship(BaseModel):
    """
    A single cell's formula logic, captured from expert interview.

    This is the atomic unit of captured knowledge. Most cells are covered
    by RowPatterns (one pattern for many cells), but cells that break the
    pattern get individual CellRelationship entries.
    """

    # Location
    sheet: str = Field(..., description="Sheet name where this cell lives")
    row: int = Field(..., description="1-indexed row number")
    col: int = Field(..., description="1-indexed column number")
    row_label: str = Field(
        ..., description="Human-readable row label, e.g. 'Revenue'"
    )
    col_label: str = Field(
        ..., description="Column label, e.g. 'Q1 2024' or 'Year 1'"
    )

    # Classification
    cell_type: CellType
    formula_type: Optional[FormulaType] = None

    # Formula specification
    formula_template: Optional[str] = Field(
        None,
        description="Excel formula template with placeholders. "
        "E.g., '={prior_col}*(1+Assumptions!$B${growth_rate_row})' "
        "Placeholders resolved at reconstruction time.",
    )
    formula_description: Optional[str] = Field(
        None,
        description="Plain English description of the calculation. "
        "E.g., 'Prior period revenue multiplied by 1 plus growth rate from Assumptions tab'",
    )

    # Dependencies
    depends_on: List[str] = Field(
        default_factory=list,
        description="List of cell references this cell depends on. "
        "Format: 'SheetName!RowLabel' or 'SheetName!R{row}C{col}'",
    )

    # Validation
    expected_value: Optional[float] = Field(
        None,
        description="Known value from the original model output. "
        "Used for verification after reconstruction.",
    )
    tolerance: float = Field(
        default=0.01,
        description="Acceptable deviation from expected value (percentage). "
        "0.01 = 1% tolerance.",
    )

    # Expert input
    expert_notes: Optional[str] = Field(
        None,
        description="Additional context from the expert. "
        "E.g., 'This uses a 8% hurdle rate but it changes by vintage year'",
    )
    confidence: float = Field(
        default=1.0,
        description="AI confidence in this relationship. "
        "1.0 = expert confirmed. <1.0 = AI inferred, needs review.",
    )


class RowPattern(BaseModel):
    """
    A repeating pattern across columns in a row.

    Most rows in a fund model follow a consistent formula pattern across
    all time periods. Capturing this as a pattern (rather than cell-by-cell)
    is more efficient and less error-prone.
    """

    sheet: str
    row: int
    row_label: str
    pattern_type: FormulaType
    formula_template: str = Field(
        ...,
        description="Template that applies to all calculated columns in this row. "
        "Uses {col}, {prior_col}, {row}, {col_letter} as placeholders.",
    )
    first_data_col: int = Field(
        ..., description="First column where this pattern applies (1-indexed)"
    )
    last_data_col: int = Field(
        ..., description="Last column where this pattern applies (1-indexed)"
    )
    seed_col: Optional[int] = Field(
        None,
        description="Column that seeds the pattern (input, not calculated). "
        "E.g., column 2 might be an input, columns 3-51 follow the pattern.",
    )
    exceptions: Dict[int, str] = Field(
        default_factory=dict,
        description="Column-specific overrides to the pattern. "
        "Key = column number, Value = formula template for that column.",
    )

    # Validation
    expected_values: Dict[int, float] = Field(
        default_factory=dict,
        description="Known values for specific columns. "
        "Key = column number, Value = expected value.",
    )

    # Expert input
    expert_notes: Optional[str] = None
    confidence: float = Field(
        default=1.0,
        description="1.0 = expert confirmed. <1.0 = AI inferred.",
    )


class SheetSpec(BaseModel):
    """
    Complete specification for one sheet in the model.

    Captures the sheet's structure, which rows are inputs vs calculated,
    and the patterns that govern calculated rows.
    """

    name: str
    purpose: str = Field(
        ...,
        description="What this sheet represents. E.g., 'Investment cash flows by quarter'",
    )

    # Structure
    header_rows: int = Field(
        default=1, description="Number of header rows before data starts"
    )
    label_cols: int = Field(
        default=1, description="Number of label columns before data starts"
    )
    total_rows: int
    total_cols: int

    # Time axis
    time_axis: str = Field(
        default="columns",
        description="Whether time periods run across columns (typical) or down rows",
    )
    time_labels: List[str] = Field(
        default_factory=list,
        description="Ordered list of time period labels. E.g., ['Q1 2024', 'Q2 2024', ...]",
    )

    # Row classifications
    input_rows: List[int] = Field(
        default_factory=list,
        description="Row numbers that are inputs (hardcoded values)",
    )
    calculated_rows: List[int] = Field(
        default_factory=list,
        description="Row numbers that are calculated from formulas",
    )

    # Row labels mapping (for verification report readability)
    row_labels: Dict[int, str] = Field(
        default_factory=dict,
        description="Mapping of row number to label. E.g., {3: 'Revenue', 4: 'COGS'}",
    )

    # Patterns (most rows follow a repeating pattern across columns)
    row_patterns: List[RowPattern] = Field(default_factory=list)

    # Individual cell overrides (for cells that break the row pattern)
    cell_overrides: List[CellRelationship] = Field(default_factory=list)

    # Sections (logical groupings of rows)
    sections: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Logical groupings of rows. "
        "E.g., [{'name': 'Revenue', 'rows': [3,4,5]}, {'name': 'Expenses', 'rows': [7,8,9,10]}]",
    )


class CrossSheetDependency(BaseModel):
    """
    A dependency from one sheet to another.

    Fund models have cascading dependencies where one sheet's calculations
    feed into another's. This captures those relationships for determining
    calculation order and tracing data flow.
    """

    source_sheet: str
    source_row_label: str
    target_sheet: str
    target_row_label: str
    relationship: str = Field(
        ...,
        description="How the target uses the source. "
        "E.g., 'Distributions.Net_Cash_Flow = CashFlows.Total - Fees.Management_Fee'",
    )


class ModelBlueprint(BaseModel):
    """
    Complete blueprint for reconstructing a fund model.

    This is the central artifact of the reverse-engineering process:
    - Produced by Phase 1 (expert interview)
    - Consumed by Phase 2 (autonomous reconstruction)

    Contains everything needed to rebuild the model with new inputs:
    sheet structures, row patterns, cell relationships, cross-sheet
    dependencies, and validation rules.
    """

    # Identity
    id: str
    name: str
    description: str
    version: str = "1.0"

    # Structure
    sheets: List[SheetSpec]
    calculation_order: List[str] = Field(
        ...,
        description="Order sheets must be calculated in. "
        "E.g., ['Assumptions', 'Cash Flows', 'Fees', 'Distributions', 'Returns']",
    )

    # Cross-sheet relationships
    cross_sheet_deps: List[CrossSheetDependency] = Field(default_factory=list)

    # All individual cell relationships (for cells not covered by RowPatterns)
    cell_relationships: List[CellRelationship] = Field(default_factory=list)

    # Validation rules
    validation_rules: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Sanity checks. E.g., 'total_distributions <= total_cash_inflows', "
        "'management_fees > 0 for all periods where NAV > 0'",
    )

    # Metadata
    expert_id: Optional[str] = None
    interview_run_id: Optional[str] = None
    created_at: Optional[datetime] = None

    # Completeness tracking
    total_calculated_cells: int = 0
    confirmed_cells: int = 0
    inferred_cells: int = 0

    @computed_field
    @property
    def completeness(self) -> float:
        """Percentage of calculated cells that have been captured."""
        if self.total_calculated_cells == 0:
            return 0.0
        return (self.confirmed_cells + self.inferred_cells) / self.total_calculated_cells

    @computed_field
    @property
    def is_complete(self) -> bool:
        """Whether all calculated cells have been captured."""
        return self.completeness >= 1.0

    def get_sheet(self, name: str) -> Optional[SheetSpec]:
        """Get a sheet spec by name."""
        for sheet in self.sheets:
            if sheet.name == name:
                return sheet
        return None

    def get_pattern_for_row(self, sheet: str, row: int) -> Optional[RowPattern]:
        """Get the row pattern for a specific row, if one exists."""
        sheet_spec = self.get_sheet(sheet)
        if not sheet_spec:
            return None
        for pattern in sheet_spec.row_patterns:
            if pattern.row == row:
                return pattern
        return None

    def get_cell_override(
        self, sheet: str, row: int, col: int
    ) -> Optional[CellRelationship]:
        """Get the cell override for a specific cell, if one exists."""
        sheet_spec = self.get_sheet(sheet)
        if not sheet_spec:
            return None
        for override in sheet_spec.cell_overrides:
            if override.row == row and override.col == col:
                return override
        return None
