import os
import logging
import sys
import random
from locust import HttpUser, task, between, TaskSet, events
from faker import Faker

# Настройка логирования
logger = logging.getLogger("load_test")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

fake = Faker("ru_RU")

# Глобальные списки для начальных данных
global_data = {
    "dish_ids": [],
    "review_ids": []
}

@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Централизованная загрузка начальных данных"""
    logger.info("### Начало нагрузочного тестирования ###")
    logger.info(f"Целевой сервер: {environment.host}")
    logger.info("Загрузка начальных данных...")
    
    try:
        with environment.client.get("/dishes", timeout=5) as response:
            if response.status_code == 200:
                global_data["dish_ids"] = [dish["id"] for dish in response.json()]
                logger.info(f"Загружено {len(global_data['dish_ids'])} блюд")
            else:
                logger.warning(f"Ошибка загрузки блюд: {response.status_code}")
                
        with environment.client.get("/reviews", timeout=5) as response:
            if response.status_code == 200:
                global_data["review_ids"] = [review["reviewId"] for review in response.json()]
                logger.info(f"Загружено {len(global_data['review_ids'])} отзывов")
            else:
                logger.warning(f"Ошибка загрузки отзывов: {response.status_code}")
                
    except Exception as e:
        logger.error(f"Ошибка загрузки начальных данных: {str(e)}")

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    logger.info("### Тест начался ###")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    logger.info("### Тест завершен ###")
    if hasattr(environment, "reviews_created"):
        logger.info(f"Создано отзывов: {environment.reviews_created}")

@events.request_success.add_listener
def my_success_handler(request_type, name, response_time, response_length, environment, **kwargs):
    """Кастомная метрика для подсчета созданных отзывов"""
    if name == "/reviews" and request_type == "POST":
        environment.reviews_created = getattr(environment, "reviews_created", 0) + 1

class UserBehavior(TaskSet):
    def __init__(self, parent):
        super().__init__(parent)
        self.dish_ids = global_data["dish_ids"]
        self.review_ids = global_data["review_ids"]
        self.friend_ids = []
        self.user_id = None
        logger.info("Инициализация виртуального пользователя")

    def on_start(self):
        """Регистрация нового пользователя"""
        try:
            logger.info("Начало регистрации пользователя")
            self.user_data = {
                "email": fake.email(),
                "login": fake.user_name(),
                "name": fake.name(),
                "birthday": fake.date_of_birth().isoformat()
            }
            
            for attempt in range(2):  # Две попытки регистрации
                with self.client.post("/users", json=self.user_data, catch_response=True, timeout=5) as response:
                    if response.status_code in [200, 201] and response.json() and "id" in response.json():
                        self.user_id = response.json()["id"]
                        logger.info(f"Успешная регистрация пользователя ID: {self.user_id}")
                        break
                    else:
                        logger.warning(f"Ошибка регистрации: {response.status_code}, попытка {attempt + 1}")
                if attempt == 1:
                    logger.error("Не удалось зарегистрировать пользователя")
                    self.interrupt()
                    
        except Exception as e:
            logger.error(f"Критическая ошибка в on_start: {str(e)}")
            self.interrupt()

    def on_stop(self):
        """Очистка данных пользователя"""
        if self.user_id:
            try:
                logger.info(f"Удаление пользователя ID: {self.user_id}")
                with self.client.delete(f"/users/{self.user_id}", catch_response=True, timeout=5) as response:
                    if response.status_code in [200, 204]:
                        logger.info(f"Пользователь ID: {self.user_id} удален")
                    else:
                        logger.warning(f"Ошибка удаления пользователя: {response.status_code}")
            except Exception as e:
                logger.error(f"Ошибка при удалении пользователя: {str(e)}")

    @task(4)
    def interact_with_dishes(self):
        """Взаимодействие с блюдами"""
        try:
            if not self.dish_ids:
                logger.warning("Список блюд пуст, пропуск задачи interact_with_dishes")
                return
                
            dish_id = random.choice(self.dish_ids)
            logger.debug(f"Просмотр блюда ID: {dish_id}")
            
            # Просмотр блюда
            with self.client.get(f"/dishes/{dish_id}", catch_response=True, timeout=5) as response:
                if response.status_code == 200:
                    logger.info(f"Успешный просмотр блюда ID: {dish_id}")
                else:
                    logger.warning(f"Ошибка просмотра блюда: {response.status_code}")
            
            # Лайк/дизлайк
            if random.random() < 0.3:
                logger.info(f"Лайк блюда ID: {dish_id}")
                with self.client.put(f"/dishes/{dish_id}/like/{self.user_id}", catch_response=True, timeout=5) as response:
                    if response.status_code != 200:
                        logger.warning(f"Ошибка лайка блюда: {response.status_code}")
            
            elif random.random() < 0.1:
                logger.info(f"Удаление лайка блюда ID: {dish_id}")
                with self.client.delete(f"/dishes/{dish_id}/like/{self.user_id}", catch_response=True, timeout=5) as response:
                    if response.status_code != 200:
                        logger.warning(f"Ошибка удаления лайка блюда: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Ошибка в interact_with_dishes: {str(e)}")

    @task(3)
    def manage_reviews(self):
        """Работа с отзывами"""
        try:
            # Написание нового отзыва
            if self.dish_ids and random.random() < 0.2:
                review_data = {
                    "content": fake.text(max_nb_chars=150),
                    "isPositive": random.choice([True, False]),
                    "userId": self.user_id,
                    "dishId": random.choice(self.dish_ids)
                }
                logger.info(f"Создание нового отзыва для блюда ID: {review_data['dishId']}")
                
                with self.client.post("/reviews", json=review_data, catch_response=True, timeout=5) as response:
                    if response.status_code == 201 and "reviewId" in response.json():
                        self.review_ids.append(response.json()["reviewId"])
                        logger.info(f"Создан отзыв ID: {response.json()['reviewId']}")
                    else:
                        logger.warning(f"Ошибка создания отзыва: {response.status_code}")

            # Взаимодействие с существующими отзывами
            if self.review_ids:
                review_id = random.choice(self.review_ids)
                logger.debug(f"Взаимодействие с отзывом ID: {review_id}")
                
                # Лайк/дизлайк
                if random.random() < 0.25:
                    logger.info(f"Лайк отзыва ID: {review_id}")
                    with self.client.put(f"/reviews/{review_id}/like/{self.user_id}", catch_response=True, timeout=5) as response:
                        if response.status_code != 200:
                            logger.warning(f"Ошибка лайка отзыва: {response.status_code}")
                
                elif random.random() < 0.1:
                    logger.info(f"Удаление лайка отзыва ID: {review_id}")
                    with self.client.delete(f"/reviews/{review_id}/like/{self.user_id}", catch_response=True, timeout=5) as response:
                        if response.status_code != 200:
                            logger.warning(f"Ошибка удаления лайка отзыва: {response.status_code}")

                # Просмотр отзыва
                with self.client.get(f"/reviews/{review_id}", catch_response=True, timeout=5) as response:
                    if response.status_code != 200:
                        logger.warning(f"Ошибка просмотра отзыва: {response.status_code}")

        except Exception as e:
            logger.error(f"Ошибка в manage_reviews: {str(e)}")

    @task(2)
    def social_interactions(self):
        """Социальные взаимодействия"""
        try:
            logger.debug("Поиск друзей...")
            with self.client.get(
                "/users",
                params={"query": fake.word(), "by": "login"},
                catch_response=True,
                timeout=5
            ) as search_response:
                if search_response.status_code == 200:
                    candidates = [u["id"] for u in search_response.json() if u["id"] != self.user_id]
                    if candidates:
                        friend_id = random.choice(candidates)
                        
                        # Добавление друга
                        if random.random() < 0.15 and friend_id not in self.friend_ids:
                            logger.info(f"Добавление друга ID: {friend_id}")
                            with self.client.put(f"/users/{self.user_id}/friends/{friend_id}", catch_response=True, timeout=5) as response:
                                if response.status_code == 200:
                                    self.friend_ids.append(friend_id)
                                else:
                                    logger.warning(f"Ошибка добавления друга: {response.status_code}")
                        
                        # Удаление друга
                        elif random.random() < 0.05 and self.friend_ids:
                            remove_id = random.choice(self.friend_ids)
                            logger.info(f"Удаление друга ID: {remove_id}")
                            with self.client.delete(f"/users/{self.user_id}/friends/{remove_id}", catch_response=True, timeout=5) as response:
                                if response.status_code == 200:
                                    self.friend_ids.remove(remove_id)
                                else:
                                    logger.warning(f"Ошибка удаления друга: {response.status_code}")

            # Просмотр своих друзей
            if self.friend_ids:
                logger.debug("Просмотр списка друзей")
                with self.client.get(f"/users/{self.user_id}/friends", catch_response=True, timeout=5) as response:
                    if response.status_code != 200:
                        logger.warning(f"Ошибка просмотра друзей: {response.status_code}")

        except Exception as e:
            logger.error(f"Ошибка в social_interactions: {str(e)}")

    @task(1)
    def user_profile_operations(self):
        """Операции с профилем"""
        try:
            # Обновление профиля
            if random.random() < 0.1:
                logger.info("Обновление профиля")
                update_data = {
                    "id": self.user_id,
                    "name": fake.name(),
                    "email": fake.email()
                }
                with self.client.put("/users", json=update_data, catch_response=True, timeout=5) as response:
                    if response.status_code != 200:
                        logger.warning(f"Ошибка обновления профиля: {response.status_code}")
            
            # Просмотр рекомендаций
            logger.debug("Получение рекомендаций")
            with self.client.get(f"/users/{self.user_id}/recommendations", catch_response=True, timeout=5) as response:
                if response.status_code != 200:
                    logger.warning(f"Ошибка получения рекомендаций: {response.status_code}")
            
            # Просмотр ленты событий
            logger.debug("Просмотр ленты событий")
            with self.client.get(f"/users/{self.user_id}/feed", catch_response=True, timeout=5) as response:
                if response.status_code != 200:
                    logger.warning(f"Ошибка просмотра ленты: {response.status_code}")

        except Exception as e:
            logger.error(f"Ошибка в user_profile_operations: {str(e)}")

class ApiUser(HttpUser):
    tasks = [UserBehavior]
    host = os.getenv("API_HOST", "http://localhost:8080")
    wait_time = between(0.5, 2.5)