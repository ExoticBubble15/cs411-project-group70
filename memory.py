class Memory:
    """
    a class, representing a stack, to store recent successful api responses

    Attributes:
        stack : a list to store api responses
        maxLength: the maximum number of items the stack can store
    """

    def __init__(self, limit):
        """
        initializes the memory as an empty array
        initializes the maxLength as an integer passed into the object
        """
        self.stack = [] #needs to always have at least 1 value
        self.maxLength = limit

    
    def stringRep(self):
        """
        returns:
            the values of the stack, in order, as a string
        """
        return str(self.stack)

    def add(self, item):
        """
        adds an item to the front of the stack
        if the stack is full, removes the last item before adding
        """
        if len(self.stack) >= self.maxLength:
            self.stack.pop(-1)
        if type(item) != list:
            item = [item]
        if len(item) > 0:
            self.stack.insert(0, item)

    def getMaxLength(self):
        """
        returns:
            the maxLength of the stack
        """
        return self.maxLength

    def getRecent(self):
        """
        attempts to return the most recent singular api response
        by traversing through its values
        
        returns:
            the most recent singular api response
            if none ^ exists, None
        """
        for i in self.stack:
            if len(i) == 1:
                return i
        return None