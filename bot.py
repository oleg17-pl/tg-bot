import config
import data


data.read_users_list_file()

def send_exception(chat_id: int, mode: str):
	exception_text = "Ошибка: "

	if mode == "only admins":
		exception_text += "Эта команда доступна только админам."
	elif mode == "only super admins":
		exception_text += "Эта команда доступна только супер-админам."
	elif mode == "ask complited":
		exception_text += "Голосование за этого пользователя уже завершено."
	elif mode == "user not exists":
		exception_text += "Такого пользователя не существует."
	elif mode == "user not filled anketa":
		exception_text += "Этот пользователь еще не заполнил свою анкету."
	elif mode == "noone filled anketa":
		exception_text += "Еще никто не заполнил анкету."

	config.bot.send_message(chat_id, exception_text)

@config.bot.message_handler(commands = ["start"])
def start_bot(message):
	this_user = data.find_users(data.User, message.from_user.username)

	if this_user:
		this_user[0].start()
	else:
		data.create_user_obj(message.from_user.username, message.chat.id).start()

	data.write_users_list_file()

@config.bot.message_handler(commands = ["info"])
def info(message):
	config.bot.send_message(message.chat.id, "Бот создал @oleg17_pl для @Amina_06_12")

@config.bot.message_handler(commands = ["questions"])
def questions_list(message):
	questions_text = "Список всех вопросов:\n\n"
	for i in range(len(config.questions)):
		questions_text += f"{i + 1}. {config.questions[i]['question']}\n"
	config.bot.send_message(message.chat.id, questions_text)

@config.bot.message_handler(commands = ["delusers"])
def delete_users(message):
	this_admin = data.find_users(data.Admin, message.from_user.username)
	if this_admin:
		if this_admin[0].status == "super":
			config.bot.send_message(message.chat.id, "Каких пользователей ты хочешь удалить из базы данных?\n\n(Напиши ники боту через запятую)")
			config.wait()
			users(message)
			config.bot.register_next_step_handler(message, __choise_delete_user)
		else:
			send_exception(message.chat.id, "only super admins")
	else:
		send_exception(message.chat.id, "only super admins")

def __choise_delete_user(message):
	if message.content_type == "text":
		formated_message = message.text.replace(" ", "")
		formated_message = formated_message.replace("@", "")
		formated_message = formated_message.replace("\n", "")

		choise_usernames = formated_message.split(",")
		founded_users = []
		non_founded_users = []

		for username in choise_usernames:
			user = data.find_users(data.User, username)
			if user:
				founded_users.append(user[0])
			else:
				non_founded_users.append(username)

		founded_users = set(founded_users)
		non_founded_users = set(non_founded_users)

		if non_founded_users:
			non_founded_text = "Эти пользователи не были найдены и не будут удалены:\n\n"
			for non_founded_user in non_founded_users:
				non_founded_text += f"@{non_founded_user}\n"

			config.bot.send_message(message.chat.id, non_founded_text)
			config.wait()

		if founded_users:
			founded_text = "Эти пользователи были найдены:\n\n"
			for founded_user in founded_users:
				founded_text += f"@{founded_user.username}\n"

			config.bot.send_message(message.chat.id, founded_text)
			config.wait()

			config.bot.send_message(message.chat.id, "Подтвердите удаление пользователей.\n\n(если согласны, введите 'Yes', если нет, то 'No')")
			config.bot.register_next_step_handler(message, __are_sure_to_delete, founded_users)

def __are_sure_to_delete(message, users_to_delete: list):
	if message.content_type == "text":
		if message.text.lower() == "yes":
			data.delete_users(users_to_delete)
			config.bot.send_message(message.chat.id, "Пользователи удалены.")
			data.write_users_list_file()

		elif message.text.lower() == "no":
			config.bot.send_message(message.chat.id, "Действие отменено.")
		else:
			config.bot.register_next_step_handler(message, __are_sure_to_delete, users_to_delete)

@config.bot.message_handler(commands = ["stats"])
def stats(message):
	if data.find_users(data.Admin, message.from_user.username):
		text = ""
		filled_ankets = 0
		added_in_group = 0

		for filler in data.find_users(data.Filler):
			if filler.selected_question == -1:
				if filler.rating_is_ended and filler.rating >= 0:
					added_in_group += 1
				filled_ankets += 1

		text += f"Количество пользователей, заполнивших анкету: {filled_ankets}\n\n"
		text += f"Количество пользователей, принятых в группу: {added_in_group}\n\n"
		text += f"Всего пользователей в базе данных бота: {len(data.find_users(data.User))}"
		config.bot.send_message(message.chat.id, text)
	else:
		send_exception(message.chat.id, "only admins")

@config.bot.message_handler(commands = ["users"])
def users(message):
	if data.find_users(data.Admin, message.from_user.username):
		if data.find_users(data.User):
			users_text = ""

			for user in data.find_users(data.User):
				users_text += f"{str(user)}\n\n"

			config.bot.send_message(message.chat.id, "Список пользователей:\n\n" + users_text, parse_mode = "HTML")
	else:
		send_exception(message.chat.id, "only admins")

@config.bot.message_handler(commands = ["submit"])
def submit(message):
	this_admin = data.find_users(data.Admin, message.from_user.username)
	if this_admin:
		if this_admin[0].status == "super":
			ended_fillers = ""

			for filler in data.find_users(data.Filler):
				if filler.selected_question == -1 and not filler.rating_is_ended :
					ended_fillers += f"<code>{filler.username}</code> (рейтинг: {filler.rating})\n"

			if not ended_fillers == "":
				text = "Голосование за каких пользователей ты хочешь завершить?\n(Напиши ники боту через запятую)\n\n"
				text += ended_fillers
				text += "\n(напиши ник пользователя боту)"
				config.bot.send_message(this_admin[0].chat_id, text, parse_mode = "HTML")
				config.bot.register_next_step_handler(message, __choise_submit)
			else:
				send_exception(this_admin[0].chat_id, "noone filled anketa")
		else:
			send_exception(message.chat.id, "only super admins")
	else:
		send_exception(message.chat.id, "only super admins")

def __choise_submit(message):
	if message.content_type == "text":
		formated_message = message.text.replace(" ", "")
		formated_message = formated_message.replace("@", "")
		formated_message = formated_message.replace("\n", "")

		choise_usernames = formated_message.split(",")
		founded_fillers = []
		non_founded_fillers = []

		for username in choise_usernames:
			filler = data.find_users(data.Filler, username)
			if filler:
				founded_fillers.append(filler[0])
			else:
				non_founded_fillers.append(username)

		if non_founded_fillers:
			text = "Эти пользователи не были найдены:\n\n"
			for non_founded_filler in non_founded_fillers:
				text += f"@{non_founded_filler}\n"

			config.bot.send_message(message.chat.id, text)
			config.wait()

		if founded_fillers:
			for filler in founded_fillers:
				if filler.selected_question == -1:
					if not filler.rating_is_ended:
						filler.end_rating()
						config.bot.send_message(message.chat.id, f"Голосование за пользователя @{filler.username} завершено.")
					else:
						send_exception(message.chat.id, "ask complited")
				else:
					send_exception(message.chat.id, "user not filled anketa")

@config.bot.message_handler(content_types = ["text", "photo"])
def some_message(message):
	this_user = data.find_users(data.User, message.from_user.username)
	if this_user:
		if isinstance(this_user[0], data.Filler):
			this_user[0].get_answer(message)
	else:
		data.create_user_obj(message.from_user.username, message.chat.id).start()
		data.write_users_list_file()

@config.bot.callback_query_handler(func = lambda callback: True)
def on_button_press(callback):
	if "add" in callback.data or "dont_add" in callback.data:
		button_data = callback.data.split(":")
		filler_to_rate = data.find_users(data.Filler, button_data[1])[0]
		admin = data.find_users(data.Admin, button_data[2])[0]

		if not filler_to_rate.rating_is_ended:
			text_to_user = ""

			if button_data[0] == "add":

				if button_data[3] == "normal":
					filler_to_rate.rating += 1
				elif button_data[3] == "super":
					filler_to_rate.rating += 2

				text_to_user += "Один из админов проголосовал за твое добавление в групппу.\n"

			elif button_data[0] == "dont_add":

				if button_data[3] == "normal":
					filler_to_rate.rating -= 1
				elif button_data[3] == "super":
					filler_to_rate.rating -= 2

				text_to_user += "Один из админов проголосовал против твоего добавления в групппу.\n"

			text_to_user += f"Твой текущий рейтинг: {filler_to_rate.rating}\n\n(если это число окажется положительным либо равному 0,\nтебя добавят в группу)"

			if not admin.last_ask_message is None:
				config.bot.edit_message_text(chat_id = admin.chat_id, message_id = admin.last_ask_message.message_id, text = admin.last_ask_message.text)
				admin.last_ask_message = None

			config.bot.send_message(filler_to_rate.chat_id, text_to_user)
			config.bot.send_message(admin.chat_id, f"Голос учтен. Текущий рейтинг @{filler_to_rate.username}: {filler_to_rate.rating}.")
			data.write_users_list_file()
		else:
			send_exception(callback.message.chat.id, "ask complited")

	elif "skip_question" in callback.data:
		button_data = callback.data.split(":")
		filler_to_skip = data.find_users(data.Filler, button_data[1])[0]
		filler_to_skip.skip_question()

config.bot.infinity_polling()