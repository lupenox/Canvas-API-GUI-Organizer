from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from canvasapi import Canvas
from my_secrets import TOKEN
import re

API_URL = "https://uwmil.instructure.com"
API_KEY = TOKEN.secret_string

@dataclass
class CourseInfo:
    id: int
    name: str
    code: Optional[str]
    state: str                  # e.g., "available", "unpublished", "completed"
    term: str                   # e.g., "Fall 2024"
    year: Optional[int]         # extracted from term/start/name/code
    start_at: Optional[str]     # raw ISO string if present

class CanvasCourseLister:
    def __init__(self, api_url: str = API_URL, api_key: str = API_KEY):
        self._canvas = Canvas(api_url, api_key)

    # --- FIXED: proper indentation + logic + args ---
    def _extract_year(
        self,
        term_name: Optional[str],
        start_at: Optional[str],
        name: Optional[str],
        code: Optional[str],
    ) -> Optional[int]:
        # 1) From term (e.g., "Fall 2024")
        if term_name:
            m = re.search(r"(20\d{2}|19\d{2})", term_name)
            if m:
                return int(m.group(1))

        # 2) From start_at ISO timestamp
        if start_at:
            try:
                dt = datetime.fromisoformat(start_at.replace("Z", "+00:00"))
                return dt.year
            except Exception:
                pass

        # 3) From course name or code (e.g., "Spring 2023", "Fall 2024", or any 4-digit year)
        for src in (name, code):
            if src:
                m = re.search(r"(Spring|Summer|Fall|Winter)\s+(20\d{2}|19\d{2})", src, re.IGNORECASE)
                if m:
                    return int(m.group(2))
                m = re.search(r"(20\d{2}|19\d{2})", src)
                if m:
                    return int(m.group(1))

        return None

    # --- FIXED: pass (name, code) into _extract_year ---
    def _to_info(self, c) -> CourseInfo:
        name = getattr(c, "name", None) or "(no name)"
        code = getattr(c, "course_code", None)
        state = getattr(c, "workflow_state", "unknown")
        term_obj = getattr(c, "term", None)
        term_name = term_obj["name"] if isinstance(term_obj, dict) and "name" in term_obj else "No term"
        start_at = getattr(c, "start_at", None)
        year = self._extract_year(term_name, start_at, name, code)
        return CourseInfo(id=c.id, name=name, code=code, state=state, term=term_name, year=year, start_at=start_at)

    def list_all_courses_grouped(self):
        user = self._canvas.get_current_user()
        print(f"Logged in as: {user.name}")

        courses = list(user.get_courses())
        infos = [self._to_info(c) for c in courses]

        now = datetime.now(timezone.utc)

        def is_future(info: CourseInfo) -> bool:
            if info.start_at:
                try:
                    dt = datetime.fromisoformat(info.start_at.replace("Z", "+00:00"))
                    return dt > now
                except Exception:
                    return False
            return bool(info.year and info.year > now.year)

        current: list[CourseInfo] = []
        future_unpublished: list[CourseInfo] = []
        past_or_completed: list[CourseInfo] = []
        unknown: list[CourseInfo] = []

        for i in infos:
            if i.state == "available":
                current.append(i)
            elif i.state in ("completed", "deleted"):
                past_or_completed.append(i)
            elif i.state == "unpublished" or is_future(i):
                future_unpublished.append(i)
            else:
                unknown.append(i)

        def print_section(title: str, items: list[CourseInfo]):
            print(f"\n=== {title} ({len(items)}) ===")
            def sort_key(k: CourseInfo):
                return (k.year or 0, k.term or "", k.name or "")
            for x in sorted(items, key=sort_key):
                yr = f"{x.year}" if x.year else "?"
                print(f"- {x.name} (id={x.id}, code={x.code}, state={x.state}, term={x.term}, year={yr})")

        print(f"Total courses: {len(infos)}")
        print_section("Active / Available", current)
        print_section("Future or Unpublished", future_unpublished)
        print_section("Completed / Past", past_or_completed)
        if unknown:
            print_section("Unknown State", unknown)
