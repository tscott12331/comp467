# Write a script that creates 24 random numbers and inserts into an array(list)
# then finds and prints the largest number along with all the numbers in that list.

from random import randint

nums: list[int] = []
AMOUNT = 24
MAX_RAND = 99 # just to keep it readable

largest = -1 # gonna keep everything positive


for _ in range(AMOUNT):
    num = randint(0, MAX_RAND)
    nums.append(num)

    if num > largest:
        largest = num

print(f"Random Numbers: {nums}")
print(f"Largest: {largest}")
