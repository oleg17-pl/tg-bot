from telebot import types
import config
import pickle
import os


__users_list = []

class User:
	def __init__(self, username: str, chat_id: int):
		self.username = username
		self.chat_id = chat_id
		self.is_started = False

	def __str__(self) -> str:
		return f"Пользователь {self.username}"

	def start(self):
		self.is_started = True

class Filler(User):
	def __init__(self, username: str, chat_id: int):
		super().__init__(username, chat_id)
		self.selected_question = 0
		self.is_complited = False
		self.is_question_asked = False
		self.last_question_message = None
		self.available_skips = 3
		self.profile = []
		self.rating = 0
		self.rating_is_ended = False

	def __str__(self) -> str:
		if not self.selected_question == -1:
			return f"Опрашиваемый <code>{self.username}</code> ответил на {self.selected_question} вопросов."
		else:
			if self.rating_is_ended and self.rating >= 0:
				return f"Опрашиваемый <code>{self.username}</code> заполнил анкету и уже добавлен в группу."
			else:
				return f"Опрашиваемый <code>{self.username}</code> заполнил анкету и имеет рейтинг {self.rating}."
				
	def start(self):
		if not self.is_started:
			config.bot.send_message(self.chat_id, f"❗️Сейчас бот задаст вам {len(config.questions)} вопросов, пожалуйста ОТВЕЧАЙТЕ ЧЕСТНО❗️")
			self.ask_question()
			self.is_started = True

	def ask_question(self):
		config.wait()
		markup = types.InlineKeyboardMarkup()

		if not self.available_skips == 0:
			skip_button = types.InlineKeyboardButton("Пропустить вопрос", callback_data = f"skip_question:{self.username}")
			markup.add(skip_button)

		last_question_message = config.bot.send_message(self.chat_id, f"{self.selected_question + 1}. {config.questions[self.selected_question]['question']}\n\n(Чтобы посмотреть список вопросов введите /questions,\nПропусков осталось: {self.available_skips})", reply_markup = markup)

		if not self.available_skips == 0:
			self.last_question_message = last_question_message
		else:
			self.last_question_message = None;

		self.is_question_asked = True

	def get_answer(self, message):
		if not self.is_complited:
			if self.is_question_asked:
				message_type = message.content_type
				is_message_expected_type = message_type == config.questions[self.selected_question]["type"]

				if message_type == "text":
					if message.text == "skip" or message.text == "пропущено" or message.text == "*пропущено*":
						if not self.available_skips == 0:
							self.skip_question()
						else:
							config.bot.send_message(self.chat_id, "Вы уже исчерпали все доступные пропуски.")
							
					elif is_message_expected_type and "/" not in message.text and not "👆" == message.text:
						self.profile.append(message.text)
						self.__answer_good()

				elif message_type == "photo" and is_message_expected_type:
					largest_photo = max(message.photo, key = lambda p: p.file_size)
					self.profile.append(largest_photo.file_id)
					self.__answer_good()
		else:
			if self.rating_is_ended and self.rating >= 0:
				config.bot.reply_to(message, f"Вы можете добавиться в группу по этой ссылке:\n{config.link_to_group}")
			else:
				config.bot.reply_to(message, "Вы уже ответили на все вопросы.")

	def skip_question(self):
		self.profile.append("*пропущено*")
		self.available_skips -= 1
		self.__answer_good()

	def __answer_good(self):
		if not self.last_question_message is None:
			config.bot.edit_message_text(chat_id = self.chat_id, message_id = self.last_question_message.message_id, text = self.last_question_message.text)
			self.last_question_message = None;

		config.bot.send_message(self.chat_id, "Спасибо за ответ!")
		self.selected_question += 1
		self.is_question_asked = False

		if self.selected_question < len(config.questions):
			self.ask_question()
		else:
			self.is_complited = True
			self.selected_question = -1
			self.show_profile()

		write_users_list_file()

	def show_profile(self):
		profile_text = ""
		profile_images = []

		for i in range(len(self.profile)):
			if config.questions[i]["type"] == "text":
				profile_text += f"{config.questions[i]['question']}\n{self.profile[i]}\n\n"
				
			elif config.questions[i]["type"] == "photo":

				if not self.profile[i] == "*пропущено*":
					profile_images.append(self.profile[i])
					profile_text += f"{config.questions[i]['question']}\n👆\n\n"
				else:
					profile_text += f"{config.questions[i]['question']}\n*пропущено*\n\n"

		config.wait()
		config.bot.send_message(self.chat_id, "Вот ваша анкета:")
		config.wait()

		if profile_images:
			for image in profile_images:
				config.bot.send_photo(self.chat_id, image)

		config.bot.send_message(self.chat_id, profile_text)
		config.wait()
		config.bot.send_message(self.chat_id, "Ваша анкета будет отправлена админам группы на рассмотрение.")

		for admin in find_users(Admin):
			admin.send_anketa(self.username, profile_text, profile_images)

		del self.is_question_asked
		del self.last_question_message
		del self.available_skips
		del self.profile

		write_users_list_file()

	def end_rating(self):
		if self.rating >= 0:
			config.bot.send_message(self.chat_id, "Поздравляем! Вас добавили в группу!")
			config.wait()
			config.bot.send_message(self.chat_id, f"Вот ссылка:\n{config.link_to_group}")
		elif self.rating < 0:
			config.bot.send_message(self.chat_id, "Админы бота отклонили вашу заявку на принятие в группу.")

		self.rating_is_ended = True
		write_users_list_file()

class Admin(User):
	def __init__(self, username: str, chat_id: int, status: str):
		super().__init__(username, chat_id)

		if status == "normal" or status == "super":
			self.status = status
		else:
			self.status = "normal"

		self.last_ask_message = None;

	def __str__(self) -> str:
		return f"Админ <code>{self.username}</code> со статусом {self.status}."

	def start(self):
		if not self.is_started:
			if self.status == "normal":
				config.bot.send_message(self.chat_id, "Ты - админ. Сюда будут приходить анкеты людей на проверку.")
			else:
				config.bot.send_message(self.chat_id, "Ты - супер-админ. Введи команду /submit чтобы завершить голосование за пользователя.")

			self.is_started = True

	def send_anketa(self, username: str, profile_text: str, images_list: list):
		for image in images_list:
			config.bot.send_photo(self.chat_id, image)

		config.bot.send_message(self.chat_id, profile_text)
		config.wait()

		markup = types.InlineKeyboardMarkup()
		button_callback_data = f"{username}:{self.username}:{self.status}"
		plus_button = types.InlineKeyboardButton("👍", callback_data = f"add:{button_callback_data}")
		minus_button = types.InlineKeyboardButton("👎", callback_data = f"dont_add:{button_callback_data}")
		markup.row(plus_button, minus_button)

		self.last_ask_message = config.bot.send_message(self.chat_id, "Добавлять этого человека в группу?", reply_markup = markup)

def read_users_list_file():
	global __users_list
	with open(config.users_list_dirrectory, "rb") as file:
		if not os.path.getsize(config.users_list_dirrectory) == 0:
			__users_list = pickle.load(file)

def write_users_list_file():
	global __users_list
	with open(config.users_list_dirrectory, "wb") as file:
		pickle.dump(__users_list, file)

def get_index_in_list(user: User) -> int:
	global __users_list
	if __users_list:
		for i in range(len(__users_list)):
			if __users_list[i].username == user.username:
				return i
	else:
		return -1

def create_user_obj(username: str, chat_id: int) -> User:
	global __users_list
	admin_found = False
	for admin in config.admins:
		if admin["username"] == username:
			admin_found = True
			break

	user_obj = None
	if admin_found:
		for admin in config.admins:
			if admin["username"] == username:
				user_obj = Admin(username, chat_id, admin["status"])
	else:
		user_obj = Filler(username, chat_id)

	add_user(user_obj)
	return user_obj

def find_users(user_type: type, username: str = None) -> list:
	global __users_list
	if not __users_list == []:
		users_by_type = []
		for user in __users_list:
			if isinstance(user, user_type):
				if username is not None:
					if user.username == username:
						users_by_type.append(user)
				else:
					users_by_type.append(user)

		return users_by_type
	else:
		return []

def add_user(user: User):
	global __users_list
	if isinstance(user, User):
		__users_list.append(user)

def delete_users(users_to_delete: list):
	global __users_list
	for user in users_to_delete:
		del __users_list[get_index_in_list(user)]