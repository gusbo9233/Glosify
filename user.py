from quiz import Quiz


class User:

    def __int__(self, user_uid, username):
        self.user_uid = user_uid
        self.username = username
        self.quizzes = []

    def add_quiz(self, quiz: Quiz):
        self.quizzes.append(quiz)

    def create_quiz(self, name):
        for quiz in self.quizzes:
            if quiz.name == name:
                return "Quiz name is already taken"

        quiz = Quiz(name)
