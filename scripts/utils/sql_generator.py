"""SQL generation utilities for Profilarr PCD format output."""


def escape_sql_string(value):
    """Escape a string for use in SQL INSERT statements."""
    if value is None:
        return "NULL"
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def escape_sql_value(value):
    """Escape any value for use in SQL - handles NULL, numbers, booleans, strings."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    return escape_sql_string(value)


def generate_insert_statement(table_name, columns, values):
    """
    Generate an INSERT statement.

    Args:
        table_name: Name of the table to insert into
        columns: List of column names
        values: List of values (must match columns length)

    Returns:
        SQL INSERT statement string
    """
    if len(columns) != len(values):
        raise ValueError(f"Column count ({len(columns)}) does not match value count ({len(values)})")

    escaped_values = [escape_sql_value(v) for v in values]
    columns_str = ", ".join(columns)
    values_str = ", ".join(escaped_values)
    return f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_str});"


class SQLBuffer:
    """Buffer for collecting SQL statements."""

    def __init__(self):
        """Initialize empty SQL buffer."""
        self.statements = []
        self.last_section = None

    def add_statement(self, statement, section=None):
        """
        Add a statement to the buffer.

        Args:
            statement: SQL statement string
            section: Optional section comment for organization
        """
        if section and section != self.last_section:
            self.add_section_header(section)
            self.last_section = section

        self.statements.append(statement)

    def add_section_header(self, section_name):
        """Add a section comment header."""
        self.statements.append(f"\n-- ============================================================================")
        self.statements.append(f"-- {section_name}")
        self.statements.append(f"-- ============================================================================\n")

    def add_insert(self, table_name, columns, values, section=None):
        """Add an INSERT statement to the buffer."""
        stmt = generate_insert_statement(table_name, columns, values)
        self.add_statement(stmt, section)

    def render(self, include_header=True):
        """
        Render the complete SQL file content.

        Args:
            include_header: Whether to include file header comment

        Returns:
            Complete SQL content as string
        """
        content = []

        if include_header:
            content.append("-- ============================================================================")
            content.append("-- PROFILARR PCD FORMAT - AUTO-GENERATED")
            content.append("-- ============================================================================\n")

        content.extend(self.statements)

        return "\n".join(content)

    def clear(self):
        """Clear the buffer."""
        self.statements = []
        self.last_section = None
