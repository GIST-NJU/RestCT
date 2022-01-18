class UnsupportedError(Exception):
    """current version cannot provided the function"""
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message
