from abc import ABC, abstractmethod

class MatrixApp(ABC):
    def __init__(self):
        self.data = {}

    @abstractmethod
    def update(self):
        """Fetch data from API (Runs in background thread)"""
        pass

    @abstractmethod
    def render(self, canvas, font, small_font):
        """Draw to the matrix"""
        pass