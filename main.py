#!/usr/bin/env python3
from canvas_client import CanvasCourseLister

if __name__ == "__main__":
    lister = CanvasCourseLister()
    data = lister.list_all_courses_grouped()
