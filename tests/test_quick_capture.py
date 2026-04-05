"""Tests for quick capture functions."""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    from scripts.quick_capture import capture_idea, capture_event, capture_task, _truncate
except ImportError:
    pytest.skip("Module not yet available", allow_module_level=True)


@pytest.mark.unit
class TestCaptureIdea:
    """Tests for capture_idea."""

    def test_creates_idea_file(self, tmp_vault: Path) -> None:
        """capture_idea should create a .md file in the vault."""
        result = capture_idea(
            vault=tmp_vault,
            text="Новая идея для продукта",
        )
        assert isinstance(result, Path)
        assert result.exists()
        assert result.suffix == ".md"

    def test_idea_has_frontmatter(self, tmp_vault: Path) -> None:
        """Created idea note should contain YAML frontmatter with type."""
        result = capture_idea(
            vault=tmp_vault,
            text="Тестовая идея",
        )
        content = result.read_text(encoding="utf-8")
        assert content.startswith("---")
        assert "type:" in content

    def test_idea_placed_in_correct_folder(self, tmp_vault: Path) -> None:
        """Idea notes should land in the strategy/ideas folder or inbox."""
        result = capture_idea(
            vault=tmp_vault,
            text="Ещё идея",
        )
        # Should be in one of: 09-СТРАТЕГИЯ/Идеи, 00-INBOX
        parent_parts = str(result.relative_to(tmp_vault)).replace("\\", "/")
        assert "09-" in parent_parts or "00-" in parent_parts or "ИДЕИ" in parent_parts.upper()


@pytest.mark.unit
class TestCaptureEvent:
    """Tests for capture_event."""

    def test_creates_event_file(self, tmp_vault: Path) -> None:
        """capture_event should create a .md file."""
        result = capture_event(
            vault=tmp_vault,
            text="Встреча с клиентом",
        )
        assert isinstance(result, Path)
        assert result.exists()

    def test_event_frontmatter_has_date(self, tmp_vault: Path) -> None:
        """Event note frontmatter should include the date."""
        result = capture_event(
            vault=tmp_vault,
            text="Конференция",
        )
        content = result.read_text(encoding="utf-8")
        assert "дата:" in content


@pytest.mark.unit
class TestCaptureTask:
    """Tests for capture_task."""

    def test_creates_task_file(self, tmp_vault: Path) -> None:
        """capture_task should create or update a .md file."""
        result = capture_task(
            vault=tmp_vault,
            text="Подготовить отчёт",
        )
        assert isinstance(result, Path)
        assert result.exists()

    def test_task_added_to_daily_record(self, tmp_vault: Path) -> None:
        """Task text should appear in the daily record."""
        result = capture_task(
            vault=tmp_vault,
            text="Закрыть тикет",
        )
        content = result.read_text(encoding="utf-8")
        assert "Закрыть тикет" in content


@pytest.mark.unit
class TestTruncateHelper:
    """Tests for _truncate utility function."""

    def test_short_string_unchanged(self) -> None:
        """Strings with fewer words than max_words should be returned as-is."""
        assert _truncate("hello world", 5) == "hello world"

    def test_long_string_truncated(self) -> None:
        """Strings with more words than max_words should be truncated."""
        result = _truncate("one two three four five six seven", 3)
        assert result == "one two three"

    def test_empty_string(self) -> None:
        """Empty string should return empty."""
        assert _truncate("", 10) == ""


# ---------------------------------------------------------------------------
# NEW TESTS — appended to increase coverage
# ---------------------------------------------------------------------------

try:
    from scripts.quick_capture import (
        _safe_filename,
        parse_frontmatter,
        _create_daily_record,
        parse_args,
    )
except ImportError:
    pass  # already skipped at module level


@pytest.mark.unit
class TestCaptureIdeaEdgeCases:
    """Edge case tests for capture_idea."""

    def test_very_long_text(self, tmp_vault: Path) -> None:
        """Long text should still create a valid file."""
        long_text = "Слово " * 200
        result = capture_idea(vault=tmp_vault, text=long_text)
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert content.startswith("---")

    def test_special_characters_in_text(self, tmp_vault: Path) -> None:
        """Special characters should be handled gracefully."""
        result = capture_idea(vault=tmp_vault, text='Идея с "кавычками" и /слэшами/')
        assert result.exists()

    def test_with_direction(self, tmp_vault: Path) -> None:
        result = capture_idea(
            vault=tmp_vault,
            text="Идея с направлением",
            direction="Развитие продукта",
        )
        content = result.read_text(encoding="utf-8")
        assert "Развитие продукта" in content

    def test_with_author(self, tmp_vault: Path) -> None:
        result = capture_idea(
            vault=tmp_vault,
            text="Авторская идея",
            author="Иванов Иван",
        )
        content = result.read_text(encoding="utf-8")
        assert "Иванов Иван" in content

    def test_with_link(self, tmp_vault: Path) -> None:
        result = capture_idea(
            vault=tmp_vault,
            text="Связанная идея",
            link="Цель Q2",
        )
        content = result.read_text(encoding="utf-8")
        assert "[[Цель Q2]]" in content

    def test_single_word(self, tmp_vault: Path) -> None:
        result = capture_idea(vault=tmp_vault, text="Минимум")
        assert result.exists()


@pytest.mark.unit
class TestCaptureEventEdgeCases:
    """Edge case tests for capture_event."""

    def test_long_text(self, tmp_vault: Path) -> None:
        long_text = "Описание " * 100
        result = capture_event(vault=tmp_vault, text=long_text)
        assert result.exists()

    def test_special_characters(self, tmp_vault: Path) -> None:
        result = capture_event(vault=tmp_vault, text='Событие: "важное" <срочно>')
        assert result.exists()

    def test_with_priority(self, tmp_vault: Path) -> None:
        result = capture_event(
            vault=tmp_vault,
            text="Срочное событие",
            priority="высокий",
        )
        content = result.read_text(encoding="utf-8")
        assert "высокий" in content

    def test_default_priority(self, tmp_vault: Path) -> None:
        result = capture_event(vault=tmp_vault, text="Обычное событие")
        content = result.read_text(encoding="utf-8")
        assert "средний" in content

    def test_with_direction(self, tmp_vault: Path) -> None:
        result = capture_event(
            vault=tmp_vault,
            text="Направленное событие",
            direction="Маркетинг",
        )
        content = result.read_text(encoding="utf-8")
        assert "Маркетинг" in content


@pytest.mark.unit
class TestCaptureTaskEdgeCases:
    """Edge case tests for capture_task."""

    def test_multiple_tasks_added(self, tmp_vault: Path) -> None:
        """Adding two tasks should result in both being present."""
        capture_task(vault=tmp_vault, text="First task")
        result = capture_task(vault=tmp_vault, text="Second task")
        content = result.read_text(encoding="utf-8")
        assert "First task" in content
        assert "Second task" in content

    def test_task_with_special_chars(self, tmp_vault: Path) -> None:
        result = capture_task(vault=tmp_vault, text='Задача с "кавычками" и [[ссылкой]]')
        content = result.read_text(encoding="utf-8")
        assert "кавычками" in content

    def test_creates_calendar_dir(self, tmp_vault: Path) -> None:
        """capture_task should ensure the calendar directory exists."""
        import shutil
        cal = tmp_vault / "08-КАЛЕНДАРЬ"
        if cal.exists():
            shutil.rmtree(cal)
        result = capture_task(vault=tmp_vault, text="New task")
        assert result.exists()
        assert cal.exists()


@pytest.mark.unit
class TestSafeFilename:
    """Tests for _safe_filename."""

    def test_removes_forbidden_chars(self) -> None:
        assert "<" not in _safe_filename("a<b>c")
        assert ":" not in _safe_filename("a:b")
        assert '"' not in _safe_filename('a"b')
        assert "?" not in _safe_filename("a?b")
        assert "*" not in _safe_filename("a*b")

    def test_preserves_normal_chars(self) -> None:
        assert _safe_filename("Normal Name") == "Normal Name"

    def test_preserves_cyrillic(self) -> None:
        assert _safe_filename("Тестовое имя") == "Тестовое имя"

    def test_strips_whitespace(self) -> None:
        assert _safe_filename("  padded  ") == "padded"


@pytest.mark.unit
class TestTruncateDetailed:
    """Additional tests for _truncate."""

    def test_exact_word_count(self) -> None:
        """If word count equals max_words, return unchanged."""
        assert _truncate("one two three", 3) == "one two three"

    def test_single_word(self) -> None:
        assert _truncate("hello", 5) == "hello"

    def test_max_words_one(self) -> None:
        assert _truncate("first second third", 1) == "first"


@pytest.mark.unit
class TestParseFrontmatter:
    """Tests for parse_frontmatter in quick_capture."""

    def test_valid(self) -> None:
        text = '---\ntitle: "Test"\ntype: note\n---\n\n# H\n'
        fm = parse_frontmatter(text)
        assert fm["title"] == "Test"

    def test_no_frontmatter(self) -> None:
        assert parse_frontmatter("Just text") == {}


@pytest.mark.unit
class TestParseArgsQuickCapture:
    """Tests for CLI argument parsing."""

    def test_idea_type(self) -> None:
        args = parse_args(["--vault", "/tmp/v", "--type", "идея", "--text", "test"])
        assert args.note_type == "идея"
        assert args.text == "test"

    def test_event_type(self) -> None:
        args = parse_args(["--vault", "/tmp/v", "--type", "событие", "--text", "ev"])
        assert args.note_type == "событие"

    def test_task_type(self) -> None:
        args = parse_args(["--vault", "/tmp/v", "--type", "задача", "--text", "task"])
        assert args.note_type == "задача"

    def test_optional_flags(self) -> None:
        args = parse_args([
            "--vault", "/tmp/v", "--type", "идея", "--text", "x",
            "--direction", "IT", "--priority", "высокий",
            "--link", "Goal", "--author", "Me",
        ])
        assert args.direction == "IT"
        assert args.priority == "высокий"
        assert args.link == "Goal"
        assert args.author == "Me"
