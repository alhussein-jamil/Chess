from enum import Enum

# Define an Enum class called Color
class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3

# Example lists
list1 = [Color.RED, Color.GREEN, Color.BLUE]
list2 = [Color.RED, Color.BLUE]

print("list1[0] == list2[0]?", list1[0] == list2[0])  # Output: True
print("list1[0] is list2[0]?", list1[0] is list2[0])    # Output: False
