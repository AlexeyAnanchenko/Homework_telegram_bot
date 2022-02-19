class EndpointHomeworkError(Exception):
    """Эндпоинт Яндекс.Домашка недоступен."""

    pass


class ApiHomeworkError(Exception):
    """Ошибка в случае обращения к API Яндекс.Домашка."""

    pass


class VariableNoneError(Exception):
    """Переменная окружения отсутствует."""

    pass


class TypeValueError(Exception):
    """Не верный тип данных в API ответе."""

    pass
