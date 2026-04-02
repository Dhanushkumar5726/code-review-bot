
import os
import math

def calculateCircleArea(radius):
    area = math.pi * radius * radius
    return area

def calculateRectangleArea(w, h):
    area = w * h
    return area

x = calculateCircleArea(5)
y = calculateRectangleArea(4, 6)
print(x, y)
