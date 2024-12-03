from contextlib import contextmanager
import re
import sqlite3

import pytest

from meal_max.models.kitchen_model import create_meal, delete_meal, get_leaderboard, get_meal_by_id, get_meal_by_name, Meal, update_meal_stats

######################################################
#
#    Fixtures
#
######################################################

def normalize_whitespace(sql_query: str) -> str:
    return re.sub(r'\s+', ' ', sql_query).strip()

# Mocking the database connection for tests
@pytest.fixture
def mock_cursor(mocker):
    mock_conn = mocker.Mock()
    mock_cursor = mocker.Mock()

    # Mock the connection's cursor
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = None  # Default return for queries
    mock_cursor.fetchall.return_value = []
    mock_cursor.commit.return_value = None

    # Mock the get_db_connection context manager from sql_utils
    @contextmanager
    def mock_get_db_connection():
        yield mock_conn  # Yield the mocked connection object

    mocker.patch("meal_max.models.kitchen_model.get_db_connection", mock_get_db_connection)

    return mock_cursor  # Return the mock cursor so we can set expectations per test

######################################################
#
#    Add and delete
#
######################################################

def test_add_meal(mock_cursor):
    """Test adding a meal to the database."""
    create_meal("Spaghetti", "Italian", 12.5, "MED")

    expected_query = normalize_whitespace("""    INSERT INTO meals (meal, cuisine, price, difficulty)
        VALUES (?, ?, ?, ?)
    """)

    actual_query = normalize_whitespace(mock_cursor.execute.call_args[0][0])

    assert actual_query == expected_query, "The SQL query did not match the expected structure."

    actual_arguments = mock_cursor.execute.call_args[0][1]
    expected_arguments = ("Spaghetti", "Italian", 12.5, "MED")
    assert actual_arguments == expected_arguments, f"The SQL query arguments did not match. Expected {expected_arguments}, got {actual_arguments}."


def test_add_meal_invalid_price():
    """Test error when trying to create a meal with an invalid price (negative or zero)."""
    with pytest.raises(ValueError, match="Invalid price: -12.5. Price must be a positive number."):
        create_meal("Spaghetti", "Italian", -12.5, "MED")

    with pytest.raises(ValueError, match="Invalid price: 0. Price must be a positive number."):
        create_meal("Spaghetti", "Italian", 0, "MED")


def test_add_meal_invalid_difficulty():
    """Test error when trying to create a meal with an invalid difficulty level."""
    with pytest.raises(ValueError, match="Invalid difficulty level: VERY_HARD. Must be 'LOW', 'MED', or 'HIGH'."):
        create_meal("Spaghetti", "Italian", 12.5, "VERY_HARD")


def test_add_meal_duplicate_name(mock_cursor):
    """Test adding a meal with a duplicate name."""
    mock_cursor.execute.side_effect = sqlite3.IntegrityError("UNIQUE constraint failed: meals.name")

    with pytest.raises(ValueError, match="Meal with name 'Spaghetti' already exists"):
        create_meal("Spaghetti", "Italian", 12.5, "MED")


def test_delete_meal(mock_cursor):
    """Test soft deleting a meal by marking it as deleted."""
    mock_cursor.fetchone.return_value = ([False])

    delete_meal(1)

    expected_select_sql = normalize_whitespace("SELECT deleted FROM meals WHERE id = ?")
    expected_update_sql = normalize_whitespace("UPDATE meals SET deleted = TRUE WHERE id = ?")

    actual_select_sql = normalize_whitespace(mock_cursor.execute.call_args_list[0][0][0])
    actual_update_sql = normalize_whitespace(mock_cursor.execute.call_args_list[1][0][0])

    assert actual_select_sql == expected_select_sql, "The SELECT query did not match the expected structure."
    assert actual_update_sql == expected_update_sql, "The UPDATE query did not match the expected structure."

    expected_select_args = (1,)
    expected_update_args = (1,)
    actual_select_args = mock_cursor.execute.call_args_list[0][0][1]
    actual_update_args = mock_cursor.execute.call_args_list[1][0][1]

    assert actual_select_args == expected_select_args, f"The SELECT query arguments did not match. Expected {expected_select_args}, got {actual_select_args}."
    assert actual_update_args == expected_update_args, f"The UPDATE query arguments did not match. Expected {expected_update_args}, got {actual_update_args}."


def test_delete_meal_bad_id(mock_cursor):
    """Test deleting a meal that does not exist."""
    mock_cursor.fetchone.return_value = None

    with pytest.raises(ValueError, match="Meal with ID 999 not found"):
        delete_meal(999)


def test_delete_meal_deleted(mock_cursor):
    """Test deleting a meal that has already been marked as deleted."""
    mock_cursor.fetchone.return_value = ([1])

    with pytest.raises(ValueError, match="Meal with ID 999 has been deleted"):
        delete_meal(999)


def test_get_meal_by_id(mock_cursor):
    """Test retrieving a meal by its ID."""
    mock_cursor.fetchone.return_value = (1, "Spaghetti", "Italian", 12.5, "MED", False)

    result = get_meal_by_id(1)
    expected_result = Meal(1, "Spaghetti", "Italian", 12.5, "MED")
    assert result == expected_result, f"Expected {expected_result}, got {result}"

    expected_query = normalize_whitespace("SELECT id, meal, cuisine, price, difficulty, deleted FROM meals WHERE id = ?")
    actual_query = normalize_whitespace(mock_cursor.execute.call_args[0][0])

    assert actual_query == expected_query, "The SQL query did not match the expected structure."

    actual_arguments = mock_cursor.execute.call_args[0][1]
    expected_arguments = (1,)
    assert actual_arguments == expected_arguments, f"The SQL query arguments did not match. Expected {expected_arguments}, got {actual_arguments}."


def test_get_meal_by_id_bad_id(mock_cursor):
    """Test retrieving a meal by an invalid ID."""
    mock_cursor.fetchone.return_value = None

    with pytest.raises(ValueError, match="Meal with ID 999 not found"):
        get_meal_by_id(999)


def test_get_meal_by_id_deleted(mock_cursor):
    """Test retrieving a meal that has been marked as deleted."""
    mock_cursor.fetchone.return_value = (1, "Spaghetti", "Italian", 12.5, "MED", True)

    with pytest.raises(ValueError, match="Meal with ID 999 has been deleted"):
        get_meal_by_id(999)


def test_get_meal_by_name(mock_cursor):
    """Test retrieving a meal by its name."""
    mock_cursor.fetchone.return_value = (1, "Spaghetti", "Italian", 12.5, "MED", False)

    result = get_meal_by_name("Sphagetti")
    expected_result = Meal(1, "Spaghetti", "Italian", 12.5, "MED")
    assert result == expected_result, f"Expected {expected_result}, got {result}"

    expected_query = normalize_whitespace("SELECT id, meal, cuisine, price, difficulty, deleted FROM meals WHERE meal = ?")
    actual_query = normalize_whitespace(mock_cursor.execute.call_args[0][0])

    assert actual_query == expected_query, "The SQL query did not match the expected structure."

    actual_arguments = mock_cursor.execute.call_args[0][1]
    expected_arguments = ("Sphagetti", )
    assert actual_arguments == expected_arguments, f"The SQL query arguments did not match. Expected {expected_arguments}, got {actual_arguments}."


def test_get_meal_by_name_bad_name(mock_cursor):
    """Test retrieving a meal by a name that does not exist."""
    mock_cursor.fetchone.return_value = None

    with pytest.raises(ValueError, match="Meal with name Motor oil not found"):
        get_meal_by_name("Motor oil")


def test_get_meal_by_name_deleted(mock_cursor):
    """Test retrieving a meal that has been marked as deleted."""
    mock_cursor.fetchone.return_value = (1, "Spaghetti", "Italian", 12.5, "MED", True)

    with pytest.raises(ValueError, match="Meal with name Sphagetti has been deleted"):
        get_meal_by_name("Sphagetti")


def test_update_meal_stats_win(mock_cursor):
    """Test updating the meal stats for a win."""
    mock_cursor.fetchone.return_value = ([False])

    update_meal_stats(1, 'win')

    expected_sql = normalize_whitespace("UPDATE meals SET battles = battles + 1, wins = wins + 1 WHERE id = ?")
    actual_sql = normalize_whitespace(mock_cursor.execute.call_args[0][0])

    assert actual_sql == expected_sql, "The SQL query did not match the expected structure."

    expected_args = (1,)
    actual_args = mock_cursor.execute.call_args[0][1]
    assert actual_args == expected_args, f"The SQL arguments did not match. Expected {expected_args}, got {actual_args}."


def test_update_meal_stats_loss(mock_cursor):
    """Test updating the meal stats for a loss."""
    mock_cursor.fetchone.return_value = ([False])

    update_meal_stats(1, 'loss')

    expected_sql = normalize_whitespace("UPDATE meals SET battles = battles + 1 WHERE id = ?")
    actual_sql = normalize_whitespace(mock_cursor.execute.call_args[0][0])

    assert actual_sql == expected_sql, "The SQL query did not match the expected structure."

    expected_args = (1,)
    actual_args = mock_cursor.execute.call_args[0][1]
    assert actual_args == expected_args, f"The SQL arguments did not match. Expected {expected_args}, got {actual_args}."


def test_update_meal_stats_bad_id(mock_cursor):
    """Test updating meal stats for a meal that does not exist."""
    mock_cursor.fetchone.return_value = None

    with pytest.raises(ValueError, match="Meal with ID 999 not found"):
        update_meal_stats(999, 'win')


def test_update_meal_stats_deleted(mock_cursor):
    """Test updating meal stats for a meal that has been marked as deleted."""
    mock_cursor.fetchone.return_value = ([1])

    with pytest.raises(ValueError, match="Meal with ID 999 has been deleted"):
        update_meal_stats(999, 'win')


def test_get_leaderboard(mock_cursor):
    """Test retrieving the leaderboard sorted by wins."""
    mock_cursor.fetchall.return_value = [
        (1, "Spaghetti", "Italian", 12.5, "MED", 10, 7, 0.7),
        (2, "Pizza", "Italian", 15.0, "LOW", 8, 5, 0.625)
    ]

    result = get_leaderboard()
    expected_result = [
        {'id': 1, 'meal': "Spaghetti", 'cuisine': "Italian", 'price': 12.5, 'difficulty': "MED", 'battles': 10, 'wins': 7, 'win_pct': 70.0},
        {'id': 2, 'meal': "Pizza", 'cuisine': "Italian", 'price': 15.0, 'difficulty': "LOW", 'battles': 8, 'wins': 5, 'win_pct': 62.5}
    ]

    assert result == expected_result, f"Expected {expected_result}, got {result}"

    expected_sql = normalize_whitespace("""    SELECT id, meal, cuisine, price, difficulty, battles, wins, (wins * 1.0 / battles) AS win_pct
        FROM meals WHERE deleted = false AND battles > 0 ORDER BY wins DESC
    """)
    actual_sql = normalize_whitespace(mock_cursor.execute.call_args[0][0])

    assert actual_sql == expected_sql, "The SQL query did not match the expected structure."


def test_get_leaderboard_sort_pct(mock_cursor):
    """Test retrieving the leaderboard sorted by win percentage."""
    mock_cursor.fetchall.return_value = [
        (1, "Spaghetti", "Italian", 12.5, "MED", 10, 7, 0.7),
        (2, "Pizza", "Italian", 15.0, "LOW", 8, 5, 0.625)
    ]

    result = get_leaderboard(sort_by="win_pct")
    expected_result = [
        {'id': 1, 'meal': "Spaghetti", 'cuisine': "Italian", 'price': 12.5, 'difficulty': "MED", 'battles': 10, 'wins': 7, 'win_pct': 70.0},
        {'id': 2, 'meal': "Pizza", 'cuisine': "Italian", 'price': 15.0, 'difficulty': "LOW", 'battles': 8, 'wins': 5, 'win_pct': 62.5}
    ]

    assert result == expected_result, f"Expected {expected_result}, got {result}"

    expected_sql = normalize_whitespace("""    SELECT id, meal, cuisine, price, difficulty, battles, wins, (wins * 1.0 / battles) AS win_pct
        FROM meals WHERE deleted = false AND battles > 0 ORDER BY win_pct DESC
    """)
    actual_sql = normalize_whitespace(mock_cursor.execute.call_args[0][0])

    assert actual_sql == expected_sql, "The SQL query did not match the expected structure."

def test_get_leaderboard_bad_sort():
    """Test retrieving the leaderboard with an invalid sort option."""
    with pytest.raises(ValueError, match="Invalid sort_by parameter: invalid_sort"):
        get_leaderboard(sort_by="invalid_sort")
