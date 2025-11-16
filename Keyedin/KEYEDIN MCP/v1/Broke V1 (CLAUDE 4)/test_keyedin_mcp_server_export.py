from keyedin_mcp_server import table_to_records

def assert_eq(a, b, msg=""):
    if a != b:
        raise AssertionError(msg or f"\nExpected:\n{b}\nGot:\n{a}")

def test_nominal():
    table = [["ColA","ColB"], ["v1","v2"], ["v3","v4"]]
    recs = table_to_records(table)
    assert_eq(recs, [{"ColA":"v1","ColB":"v2"},{"ColA":"v3","ColB":"v4"}])

def test_short_row_padded():
    table = [["A","B","C"], ["1","2"], ["3","4","5","EXTRA"]]
    recs = table_to_records(table)
    assert_eq(recs[0], {"A":"1","B":"2","C":""})
    assert_eq(recs[1], {"A":"3","B":"4","C":"5"})

def test_empty_table():
    assert_eq(table_to_records([]), [])

def test_no_headers():
    assert_eq(table_to_records([[],["x","y"]]), [])

if __name__ == "__main__":
    test_nominal()
    test_short_row_padded()
    test_empty_table()
    test_no_headers()
    print("All tests passed.")