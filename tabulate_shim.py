"""
Helper utility to format and print pandas DataFrames in clean ASCII tables.
Avoids requiring external heavy dependencies while producing clean CLI tables.
"""
import pandas as pd


def print_table(df: pd.DataFrame):
    """Prints a DataFrame in a clean, aligned tabular format."""
    if df.empty:
        print("(No data available)")
        return

    # Convert all values to string
    df_str = df.astype(str)
    headers = list(df.columns)
    
    # Calculate column widths
    col_widths = {
        col: max(len(col), df_str[col].map(len).max())
        for col in headers
    }

    # Header row
    header_line = " | ".join(f"{col:<{col_widths[col]}}" for col in headers)
    separator = "-+-".join("-" * col_widths[col] for col in headers)

    print(header_line)
    print(separator)

    # Data rows
    for _, row in df_str.iterrows():
        row_line = " | ".join(f"{row[col]:<{col_widths[col]}}" for col in headers)
        print(row_line)
