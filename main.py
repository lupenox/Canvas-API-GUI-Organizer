#!/usr/bin/env python3
from canvas_client import CanvasCourseLister

if __name__ == "__main__":
    lister = CanvasCourseLister()
    lister.list_all_courses_grouped()
