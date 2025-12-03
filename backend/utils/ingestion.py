# ingestion.py (FINAL)

import pandas as pd
import json
from io import StringIO
from typing import List, Dict, Any, Tuple

# --- Data Model ---


class SpreadsheetRow:
    """
    Represents a single row in a spreadsheet as a semantic concept.
    """
    def __init__(
        self,
        sheet_name: str,
        row_index: int,
        row_header: str,
        values: List[Any],
        context_tags: List[str] = None,
    ):
        self.sheet_name = sheet_name
        self.row_index = row_index
        self.row_header = row_header if row_header else "Unknown Metric"
        self.values = values
        self.context_tags = context_tags or []

        # This is the "Magic Text" the AI will actually read
        self.semantic_text = self._generate_semantic_text()

    def _generate_semantic_text(self) -> str:
        """Creates a natural language description of this row for embedding."""
        # Convert values to a string sample (first 3 non-empty values)
        sample_vals = [str(v) for v in self.values if pd.notna(v)][:3]
        val_str = ", ".join(sample_vals)

        return (
            f"Sheet: {self.sheet_name}. "
            f"Metric: {self.row_header}. "
            f"Context: {', '.join(self.context_tags)}. "
            f"Contains values like: {val_str}."
        )

    def to_dict(self):
        return {
            "metadata": {
                "sheet": self.sheet_name,
                "row_idx": self.row_index,
                "header": self.row_header,
            },
            "document": self.semantic_text,
        }


# --- Core row processing helper ---


def _process_dataframe(df: pd.DataFrame, sheet_name: str) -> List[SpreadsheetRow]:
    """
    Shared logic that takes a pandas DataFrame and converts it into SpreadsheetRow objects.
    Used both by the CSV-based parser and the Excel SheetParser.
    """
    semantic_rows: List[SpreadsheetRow] = []

    # Heuristic 1: Find the "Header Row" (usually row 0 or the first row
    # with more than 2 string entries)
    header_row_idx = 0
    for i, row in df.iterrows():
        # Look for the first row with more than 2 string entries
        str_count = row.apply(lambda x: isinstance(x, str)).sum()
        if str_count > 2:
            header_row_idx = i
            break

    # Extract column context (e.g., "Year 1", "Revenue")
    col_headers = df.iloc[header_row_idx].fillna("").astype(str).tolist()

    # Heuristic 2: Identify "Index Column" (Where the metric names are)
    index_col_idx = 0

    # Iterate through data rows (skipping header)
    for i in range(header_row_idx + 1, len(df)):
        row = df.iloc[i]

        metric_name = row[index_col_idx]

        if pd.isna(metric_name) or str(metric_name).strip() == "":
            continue

        # Check if row has numeric data starting from the column after the metric name
        numeric_values = pd.to_numeric(row[index_col_idx + 1 :], errors="coerce")
        if numeric_values.notna().sum() == 0:
            continue

        # Create the Semantic Object
        row_obj = SpreadsheetRow(
            sheet_name=sheet_name,
            row_index=i,
            row_header=str(metric_name).strip(),
            values=row[index_col_idx + 1 :].tolist(),
            context_tags=col_headers,
        )
        semantic_rows.append(row_obj)

    return semantic_rows


# --- CSV-string-based parser (kept for compatibility, not used by current upload flow) ---


def parse_spreadsheet_content(file_name: str, content: str) -> List[SpreadsheetRow]:
    """
    Parses the raw CSV content string into a list of SpreadsheetRow objects.
    The file_name is used as the 'sheet' context tag.

    NOTE: This is only used if you send CSV text to the backend.
    With the current React + FastAPI file upload, we instead use SheetParser
    on the saved .xlsx files.
    """
    print(f"Parsing CSV content for: {file_name}")
    try:
        data = StringIO(content)
        df = pd.read_csv(data, header=None)
        return _process_dataframe(df, file_name)
    except Exception as e:
        print(f"Error parsing content for {file_name}: {e}")
        return []


# --- Excel file parser used by index_data.py ---


class SheetParser:
    """
    Parses a real Excel file (.xlsx / .xls) into SpreadsheetRow objects.

    Used by:
      - index_data.index_spreadsheet_data()
      - indirectly by /index endpoint in api/main.py
    """

    def __init__(self, file_path: str):
        self.file_path = file_path

    def parse(self) -> List[SpreadsheetRow]:
        print(f"\n📄 SheetParser: reading Excel file: {self.file_path}")
        try:
            # Read all sheets, no header so our heuristic can find the header row
            xls = pd.read_excel(self.file_path, sheet_name=None, header=None)
        except Exception as e:
            print(f"❌ Error reading Excel file {self.file_path}: {e}")
            return []

        all_rows: List[SpreadsheetRow] = []

        for sheet_name, df in xls.items():
            try:
                rows = _process_dataframe(df, sheet_name=sheet_name)
                print(f"   Sheet '{sheet_name}': {len(rows)} semantic rows")
                all_rows.extend(rows)
            except Exception as e:
                print(f"   ❌ Error processing sheet '{sheet_name}': {e}")

        print(f"📊 Total rows parsed from {self.file_path}: {len(all_rows)}")
        return all_rows
