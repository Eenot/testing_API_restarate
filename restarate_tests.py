import pytest
import requests
import time

BASE_DISH_URL = "http://localhost:8080/dishes"
BASE_CATEGORY_URL = "http://localhost:8080/categories"
BASE_USER_URL = "http://localhost:8080/users"
BASE_PRICING_URL = "http://localhost:8080/pricing"
BASE_AUTHORS_URL = "http://localhost:8080/authors"
BASE_REVIEWS_URL = "http://localhost:8080/reviews"

TEST_REVIEW = {
    "content": "Отличное блюдо!",
    "isPositive": True,
    "userId": 1,
    "dishId": 1
}

TEST_USER = {
    "email": "user@example.com",
    "login": "test_user",
    "name": "Test User",
    "birthday": "1990-01-01"
}

TEST_DISH = {
    "name": "Test Dish",
    "description": "Test Description",
    "releaseDate": "2023-01-01",
    "weight": 300,
    "pricing": {"id": 1},
    "categories": [{"id": 1}],
    "authors": [{"id": 1}]
}

EXPECTED_PRICING_CATEGORIES = {
    1: "$",
    2: "$$",
    3: "$$$",
    4: "$$$$",
    5: "$$$$$"
}

if __name__ == "__main__":
    # Явный запуск pytest при выполнении скрипта
    retcode = pytest.main(["-v", __file__])
    if retcode != 0:
        raise RuntimeError(f"Тесты завершились с ошибкой (код {retcode})")

@pytest.fixture(autouse=True)
def cleanup():
    yield
    response = requests.get(BASE_DISH_URL)
    for dish in response.json():
        requests.delete(f"{BASE_DISH_URL}/{dish['id']}")

def test_create_and_get_dish():
    print("\n=== Запуск test_create_and_get_dish ===")
    # Тест создания и получения блюда
    response = requests.post(BASE_DISH_URL, json=TEST_DISH)
    assert response.status_code == 200
    dish_id = response.json()["id"]
    
    # Проверка получения по ID
    get_response = requests.get(f"{BASE_DISH_URL}/{dish_id}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Test Dish"

def test_update_dish():
    # Тест обновления блюда
    created = requests.post(BASE_DISH_URL, json=TEST_DISH).json()
    
    updated_data = {**TEST_DISH, "name": "Updated Dish"}
    update_response = requests.put(BASE_DISH_URL, json=updated_data)
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Updated Dish"

def test_like_dislike_mechanism():
    # Тест системы лайков/дизлайков
    dish = requests.post(BASE_DISH_URL, json=TEST_DISH).json()
    user_id = 123
    
    # Добавление лайка
    like_response = requests.put(f"{BASE_DISH_URL}/{dish['id']}/like/{user_id}")
    assert like_response.status_code == 200
    
    # Проверка популярных блюд
    popular = requests.get(f"{BASE_DISH_URL}/popular?count=1").json()
    assert len(popular) == 1
    
    # Удаление лайка
    requests.delete(f"{BASE_DISH_URL}/{dish['id']}/like/{user_id}")
    popular_after = requests.get(f"{BASE_DISH_URL}/popular?count=1").json()
    assert len(popular_after) == 0

def test_search_functionality():
    # Тест поиска блюд
    test_dishes = [
        {**TEST_DISH, "name": "Борщ Украинский"},
        {**TEST_DISH, "name": "Салат Цезарь"}
    ]
    for dish in test_dishes:
        requests.post(BASE_DISH_URL, json=dish)
    
    # Поиск по названию
    search_response = requests.get(
        f"{BASE_DISH_URL}/search?query=цезарь&by=title"
    )
    assert search_response.status_code == 200
    assert any("Цезарь" in d["name"] for d in search_response.json())

def test_author_dishes():
    # Тест получения блюд автора
    author_id = 1
    for _ in range(3):
        requests.post(BASE_DISH_URL, json={**TEST_DISH, "authors": [{"id": author_id}]})
    
    response = requests.get(f"{BASE_DISH_URL}/author/{author_id}?sortBy=name")
    assert response.status_code == 200
    assert len(response.json()) == 3

def test_validation():
    # Тест валидации входных данных
    invalid_dish = {**TEST_DISH}
    invalid_dish["weight"] = -100  # Неправильный вес
    
    response = requests.post(BASE_DISH_URL, json=invalid_dish)
    assert response.status_code == 400
    assert "positive" in response.text.lower()

def test_delete_dish():
    # Тест удаления блюда
    created = requests.post(BASE_DISH_URL, json=TEST_DISH).json()
    
    delete_response = requests.delete(f"{BASE_DISH_URL}/{created['id']}")
    assert delete_response.status_code == 200
    
    get_response = requests.get(f"{BASE_DISH_URL}/{created['id']}")
    assert get_response.status_code == 404

def test_common_dishes():
    # Тест общих популярных блюд
    user_id = 1
    friend_id = 2
    
    # Создание тестовых данных
    dish1 = requests.post(BASE_DISH_URL, json=TEST_DISH).json()
    dish2 = requests.post(BASE_DISH_URL, json={**TEST_DISH, "name": "Dish 2"}).json()
    
    # Добавление лайков
    requests.put(f"{BASE_DISH_URL}/{dish1['id']}/like/{user_id}")
    requests.put(f"{BASE_DISH_URL}/{dish1['id']}/like/{friend_id}")
    requests.put(f"{BASE_DISH_URL}/{dish2['id']}/like/{user_id}")
    
    response = requests.get(f"{BASE_DISH_URL}/common?userId={user_id}&friendId={friend_id}")
    assert response.status_code == 200
    assert len(response.json()) >= 1

def test_pagination_and_filters():
    # Тест пагинации и фильтров
    for i in range(15):
        requests.post(BASE_DISH_URL, json={**TEST_DISH, "name": f"Dish {i}"})
    
    # Проверка пагинации
    response = requests.get(f"{BASE_DISH_URL}/popular?count=5")
    assert response.status_code == 200
    assert len(response.json()) == 5
    
    # Проверка фильтра по году
    response = requests.get(f"{BASE_DISH_URL}/popular?year=2023")
    assert response.status_code == 200
    assert len(response.json()) > 0

# Тесты для контроллера UserController
@pytest.fixture(autouse=True)
def user_cleanup():
    yield
    # Очистка пользователей после каждого теста
    response = requests.get(BASE_USER_URL)
    if response.status_code == 200:
        for user in response.json():
            requests.delete(f"{BASE_USER_URL}/{user['id']}")

def test_create_and_get_user():
    # Тест создания пользователя
    response = requests.post(BASE_USER_URL, json=TEST_USER)
    assert response.status_code == 200
    user_id = response.json()["id"]
    
    # Проверка получения пользователя
    get_response = requests.get(f"{BASE_USER_URL}/{user_id}")
    assert get_response.status_code == 200
    assert get_response.json()["login"] == "test_user"

def test_friend_management():
    # Тест системы друзей
    user1 = requests.post(BASE_USER_URL, json=TEST_USER).json()
    user2 = requests.post(BASE_USER_URL, json={
        **TEST_USER, 
        "login": "friend_user"
    }).json()
    
    # Добавление друга
    add_response = requests.put(
        f"{BASE_USER_URL}/{user1['id']}/friends/{user2['id']}"
    )
    assert add_response.status_code == 200
    
    # Проверка списка друзей
    friends = requests.get(f"{BASE_USER_URL}/{user1['id']}/friends").json()
    assert len(friends) == 1
    assert friends[0]["id"] == user2["id"]
    
    # Удаление друга
    requests.delete(f"{BASE_USER_URL}/{user1['id']}/friends/{user2['id']}")
    friends_after = requests.get(f"{BASE_USER_URL}/{user1['id']}/friends").json()
    assert len(friends_after) == 0

def test_common_friends():
    # Тест общих друзей
    user1 = requests.post(BASE_USER_URL, json=TEST_USER).json()
    user2 = requests.post(BASE_USER_URL, json={**TEST_USER, "login": "user2"}).json()
    common_friend = requests.post(BASE_USER_URL, json={**TEST_USER, "login": "common"}).json()
    
    # Добавление общего друга
    requests.put(f"{BASE_USER_URL}/{user1['id']}/friends/{common_friend['id']}")
    requests.put(f"{BASE_USER_URL}/{user2['id']}/friends/{common_friend['id']}")
    
    # Проверка общих друзей
    response = requests.get(
        f"{BASE_USER_URL}/{user1['id']}/friends/common/{user2['id']}"
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == common_friend["id"]

def test_user_validation():
    # Тест валидации данных
    invalid_user = {
        "email": "invalid-email",
        "login": " ",
        "birthday": "2050-01-01"
    }
    
    response = requests.post(BASE_USER_URL, json=invalid_user)
    assert response.status_code == 400
    assert "email" in response.text.lower()
    assert "past" in response.text.lower()

def test_user_recommendations():
    # Тест рекомендаций
    user = requests.post(BASE_USER_URL, json=TEST_USER).json()
    response = requests.get(f"{BASE_USER_URL}/{user['id']}/recommendations")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_user_feed():
    # Тест ленты событий
    user = requests.post(BASE_USER_URL, json=TEST_USER).json()
    response = requests.get(f"{BASE_USER_URL}/{user['id']}/feed")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_user_update():
    # Тест обновления данных
    user = requests.post(BASE_USER_URL, json=TEST_USER).json()
    updated_data = {**user, "name": "Updated Name"}
    
    response = requests.put(BASE_USER_URL, json=updated_data)
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"

def test_user_deletion():
    # Тест удаления пользователя
    user = requests.post(BASE_USER_URL, json=TEST_USER).json()
    delete_response = requests.delete(f"{BASE_USER_URL}/{user['id']}")
    assert delete_response.status_code == 200
    
    get_response = requests.get(f"{BASE_USER_URL}/{user['id']}")
    assert get_response.status_code == 404

#Тесты для контроллера CategoryController
@pytest.fixture(autouse=True)
def category_cleanup():
    yield
    # Очистка тестовых данных при необходимости

def test_get_all_categories():
    response = requests.get(BASE_CATEGORY_URL)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    if len(response.json()) > 0:
        assert "id" in response.json()[0]
        assert "name" in response.json()[0]

def test_get_category_by_id():
    # Предполагаем, что категория с ID=1 существует
    response = requests.get(f"{BASE_CATEGORY_URL}/1")
    
    if response.status_code == 200:
        category = response.json()
        assert isinstance(category, dict)
        assert category["id"] == 1
        assert isinstance(category["name"], str)
    elif response.status_code == 404:
        pytest.skip("Категория с ID=1 не найдена")

def test_nonexistent_category():
    response = requests.get(f"{BASE_CATEGORY_URL}/99999")
    assert response.status_code == 404

def test_category_validation():
    # Тест валидации для несуществующей категории
    invalid_id_response = requests.get(f"{BASE_CATEGORY_URL}/invalid_id")
    assert invalid_id_response.status_code == 400

def test_category_structure():
    # Проверка структуры ответа
    response = requests.get(BASE_CATEGORY_URL)
    if len(response.json()) > 0:
        category = response.json()[0]
        assert set(category.keys()) == {"id", "name"}
        assert isinstance(category["id"], int)
        assert isinstance(category["name"], str)

#Тесты для контроллера PricingController
def test_get_all_pricing_categories():
    response = requests.get(BASE_PRICING_URL)
    assert response.status_code == 200
    
    categories = response.json()
    assert len(categories) == 5, "Должно быть ровно 5 ценовых категорий"
    
    # Проверка соответствия ID и названий
    for category in categories:
        assert category["id"] in EXPECTED_PRICING_CATEGORIES
        assert category["name"] == EXPECTED_PRICING_CATEGORIES[category["id"]]

def test_get_valid_pricing_category():
    for category_id in EXPECTED_PRICING_CATEGORIES:
        response = requests.get(f"{BASE_PRICING_URL}/{category_id}")
        assert response.status_code == 200
        category = response.json()
        assert category["id"] == category_id
        assert category["name"] == EXPECTED_PRICING_CATEGORIES[category_id]

def test_nonexistent_pricing_categories():
    invalid_ids = [0, 6, 999]
    for category_id in invalid_ids:
        response = requests.get(f"{BASE_PRICING_URL}/{category_id}")
        assert response.status_code == 404

def test_pricing_category_order():
    response = requests.get(BASE_PRICING_URL)
    categories = response.json()
    
    # Проверка порядка категорий по ID
    ids = [c["id"] for c in categories]
    assert ids == [1, 2, 3, 4, 5], "Категории должны быть упорядочены по ID"
    
    # Проверка соответствия названий порядку
    names = [c["name"] for c in categories]
    assert names == ["$", "$$", "$$$", "$$$$", "$$$$$"]

def test_invalid_id_formats():
    test_cases = [
        ("invalid", 400),
        ("1.5", 400),
        ("-1", 400),
        ("0", 404),
        ("6", 404)
    ]
    
    for test_id, expected_status in test_cases:
        response = requests.get(f"{BASE_PRICING_URL}/{test_id}")
        assert response.status_code == expected_status


#Тесты для AuthorController
@pytest.fixture(autouse=True)
def author_cleanup():
    yield
    # Очистка тестовых данных
    response = requests.get(BASE_AUTHORS_URL)
    for author in response.json():
        requests.delete(f"{BASE_AUTHORS_URL}/{author['id']}")

def test_create_author():
    author_data = {"name": "Иван Петров"}
    response = requests.post(BASE_AUTHORS_URL, json=author_data)
    assert response.status_code == 200
    created = response.json()
    assert "id" in created
    assert created["name"] == "Иван Петров"

def test_get_all_authors():
    # Создаём 3 тестовых автора
    for name in ["Автор 1", "Автор 2", "Автор 3"]:
        requests.post(BASE_AUTHORS_URL, json={"name": name})
    
    response = requests.get(BASE_AUTHORS_URL)
    assert response.status_code == 200
    assert len(response.json()) == 3

def test_get_author_by_id():
    # Создаём и получаем автора
    author = requests.post(BASE_AUTHORS_URL, json={"name": "Тестовый автор"}).json()
    
    response = requests.get(f"{BASE_AUTHORS_URL}/{author['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Тестовый автор"

def test_update_author():
    # Создание и обновление
    author = requests.post(BASE_AUTHORS_URL, json={"name": "Старое имя"}).json()
    updated = {**author, "name": "Новое имя"}
    
    response = requests.put(BASE_AUTHORS_URL, json=updated)
    assert response.status_code == 200
    assert response.json()["name"] == "Новое имя"

def test_delete_author():
    author = requests.post(BASE_AUTHORS_URL, json={"name": "Удаляемый автор"}).json()
    
    # Удаление
    delete_response = requests.delete(f"{BASE_AUTHORS_URL}/{author['id']}")
    assert delete_response.status_code == 200
    
    # Проверка существования
    get_response = requests.get(f"{BASE_AUTHORS_URL}/{author['id']}")
    assert get_response.status_code == 404

def test_author_validation():
    # Тест валидации имени
    tests = [
        ({"name": ""}, 400),        # Пустое имя
        ({"name": "   "}, 400),      # Пробелы
        ({"invalid": "field"}, 400), # Неправильное поле
        ({"name": "A"}, 200),        # Короткое но валидное
        ({"name": "X"*255}, 200)     # Длинное имя
    ]
    
    for data, expected_status in tests:
        response = requests.post(BASE_AUTHORS_URL, json=data)
        assert response.status_code == expected_status

def test_nonexistent_author_operations():
    # Тест операций с несуществующим автором
    response = requests.get(f"{BASE_AUTHORS_URL}/999999")
    assert response.status_code == 404
    
    response = requests.delete(f"{BASE_AUTHORS_URL}/999999")
    assert response.status_code == 404
    
    response = requests.put(BASE_AUTHORS_URL, json={"id": 999999, "name": "Test"})
    assert response.status_code == 404

def test_author_unique_constraint():
    # Тест уникальности имени (если предусмотрено)
    requests.post(BASE_AUTHORS_URL, json={"name": "Уникальный автор"})
    
    response = requests.post(BASE_AUTHORS_URL, json={"name": "Уникальный автор"})
    # Если уникальность требуется:
    # assert response.status_code == 409
    # Если разрешены дубли:
    assert response.status_code == 200

#Тесты для ReviewController
@pytest.fixture(autouse=True)
def review_cleanup():
    yield
    # Очистка тестовых данных
    response = requests.get(BASE_REVIEWS_URL)
    for review in response.json():
        requests.delete(f"{BASE_REVIEWS_URL}/{review['reviewId']}")

def test_create_and_get_review():
    # Создание отзыва
    response = requests.post(BASE_REVIEWS_URL, json=TEST_REVIEW)
    assert response.status_code == 200
    review_id = response.json()["reviewId"]
    
    # Получение по ID
    get_response = requests.get(f"{BASE_REVIEWS_URL}/{review_id}")
    assert get_response.status_code == 200
    assert get_response.json()["content"] == "Отличное блюдо!"

def test_update_review():
    # Создание и обновление
    review = requests.post(BASE_REVIEWS_URL, json=TEST_REVIEW).json()
    updated = {**review, "content": "Обновленный отзыв"}
    
    response = requests.put(BASE_REVIEWS_URL, json=updated)
    assert response.status_code == 200
    assert response.json()["content"] == "Обновленный отзыв"

def test_delete_review():
    # Создание и удаление
    review = requests.post(BASE_REVIEWS_URL, json=TEST_REVIEW).json()
    
    delete_response = requests.delete(f"{BASE_REVIEWS_URL}/{review['reviewId']}")
    assert delete_response.status_code == 200
    
    get_response = requests.get(f"{BASE_REVIEWS_URL}/{review['reviewId']}")
    assert get_response.status_code == 404

def test_review_list():
    # Тест пагинации и фильтрации
    for i in range(15):
        requests.post(BASE_REVIEWS_URL, json={
            **TEST_REVIEW,
            "dishId": 1 if i < 10 else 2
        })
    
    # Проверка фильтра по dishId
    filtered = requests.get(f"{BASE_REVIEWS_URL}?dishId=1&count=5").json()
    assert len(filtered) == 5
    assert all(r["dishId"] == 1 for r in filtered)
    
    # Проверка пагинации
    all_reviews = requests.get(f"{BASE_REVIEWS_URL}?count=20").json()
    assert len(all_reviews) == 15

def test_like_dislike_flow():
    # Полный цикл работы с лайками
    review = requests.post(BASE_REVIEWS_URL, json=TEST_REVIEW).json()
    user_id = 123
    
    # Добавление лайка
    like_response = requests.put(
        f"{BASE_REVIEWS_URL}/{review['reviewId']}/like/{user_id}"
    )
    assert like_response.status_code == 200
    
    # Проверка полезности
    updated_review = requests.get(
        f"{BASE_REVIEWS_URL}/{review['reviewId']}"
    ).json()
    assert updated_review["useful"] == 1
    
    # Удаление лайка
    delete_like_response = requests.delete(
        f"{BASE_REVIEWS_URL}/{review['reviewId']}/like/{user_id}"
    )
    assert delete_like_response.status_code == 200
    
    # Проверка после удаления
    updated_review = requests.get(
        f"{BASE_REVIEWS_URL}/{review['reviewId']}"
    ).json()
    assert updated_review["useful"] == 0

def test_review_validation():
    # Тест валидации данных
    tests = [
        ({**TEST_REVIEW, "content": ""}, 400),  # Пустой контент
        ({**TEST_REVIEW, "isPositive": "not_bool"}, 400),  # Неправильный тип
        ({**TEST_REVIEW, "userId": -1}, 400),  # Отрицательный userId
        ({**TEST_REVIEW, "dishId": 0}, 400),  # Некорректный dishId
        ({**TEST_REVIEW, "content": "X"*201}, 400)  # Слишком длинный контент
    ]
    
    for data, expected_status in tests:
        response = requests.post(BASE_REVIEWS_URL, json=data)
        assert response.status_code == expected_status

def test_duplicate_likes():
    # Проверка повторных лайков
    review = requests.post(BASE_REVIEWS_URL, json=TEST_REVIEW).json()
    user_id = 456
    
    # Двойной лайк
    requests.put(f"{BASE_REVIEWS_URL}/{review['reviewId']}/like/{user_id}")
    response = requests.put(
        f"{BASE_REVIEWS_URL}/{review['reviewId']}/like/{user_id}"
    )
    assert response.status_code == 409  # Конфликт

def test_cross_operations():
    # Тест взаимного влияния лайков/дизлайков
    review = requests.post(BASE_REVIEWS_URL, json=TEST_REVIEW).json()
    user_id = 789
    
    # Добавление лайка
    requests.put(f"{BASE_REVIEWS_URL}/{review['reviewId']}/like/{user_id}")
    
    # Попытка добавить дизлайк
    response = requests.put(
        f"{BASE_REVIEWS_URL}/{review['reviewId']}/dislike/{user_id}"
    )
    assert response.status_code == 409  # Конфликт

def test_review_structure():
    # Проверка структуры ответа
    review = requests.post(BASE_REVIEWS_URL, json=TEST_REVIEW).json()
    expected_keys = {
        "reviewId", "content", "isPositive",
        "userId", "dishId", "useful"
    }
    assert set(review.keys()) == expected_keys