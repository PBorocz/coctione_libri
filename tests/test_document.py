"""Test User data type."""

import time
from datetime import datetime

import pytest

from app.models import Category
from app.models.document import Document


################################################################################
# Utility methods
################################################################################
def get_current_row_count():
    return len(list(Document.select()))


################################################################################
# Tests
################################################################################
def test_document_instantiation(app, document_and_user):
    document, user = document_and_user

    # Confirm
    assert document.user_id, "Sorry, document needs a user!"
    assert document.created
    assert not document.updated
    assert document.category == Category.COOKING_RECIPES
    assert document.mimetype == "application/pdf"


def test_document_save(app, document_and_user):
    """Test that we can successfully save a user instance."""
    document, user = document_and_user

    row_count = get_current_row_count()
    assert not document.id
    assert not document.updated

    # Test
    document.save()

    # Confirm
    assert isinstance(document, Document)
    assert document.id
    assert not document.updated
    assert get_current_row_count() == row_count + 1


def test_document_delete_non_existing(app, document_and_user):
    """Test that delete an instance that hasn't been saved yet is OK."""
    _, user = document_and_user

    # Setup
    test_document_parms = {
        "user": user,
        "title": "a Document Title",
    }
    doc = Document(**test_document_parms)

    # Test
    count = doc.delete_instance()

    # Confirm
    assert 0 == count


def test_document_delete_existing(app, document_and_user):
    document, user = document_and_user

    # Setup
    document.save()
    assert get_current_row_count() == 1

    # Test
    count = document.delete_instance()

    # Confirm
    assert count == 1
    assert get_current_row_count() == 0


def test_document_update(app, document_and_user):
    """Test ability to update a document."""
    document, user = document_and_user
    # Setup
    document.save()

    # Test
    ############################################################################
    document.title = "another Title"
    document.save()

    # Confirm
    assert document.updated  # We did a REAL update now!
    q_document = Document.get(Document.id == document.id)
    assert "another Title" == q_document.title


def test_document_queries(app, document_and_user):
    document, user = document_and_user

    # Setup
    document.save()

    # Test - Title
    q_docs = Document.select().where(Document.title == document.title)
    assert len(q_docs) == 1
    q_document = q_docs[0]
    assert isinstance(q_document, Document)
    assert q_document.id
    assert q_document.title == document.title

    # Test - Category
    Document.get(Document.category == Category.COOKING_RECIPES)

    # Test - Nothing
    with pytest.raises(Document.DoesNotExist):
        Document.get(Document.title == "does NOT exist!")


def test_document_tags(app, document_and_user):
    """Test ability to update json list field."""
    document, user = document_and_user
    # Setup
    document.save()
    assert not document.tags

    ############################################################################
    # Test 1 - Single entry, make sure it's lowercase.
    ############################################################################
    document.tags_add("aTestTag")
    document.save()

    # Confirm
    assert document.updated  # We did a REAL update now!
    q_document = Document.get(Document.id == document.id)
    assert "atesttag" == q_document.tags

    ############################################################################
    # Test 2 - Second entry, before current one!
    ############################################################################
    document.tags_add("AnotherTag")
    document.save()

    # Confirm
    q_document = Document.get(Document.id == document.id)
    assert "atesttag|anothertag" == q_document.tags
    assert ["anothertag", "atesttag"] == q_document.tags_split
    assert ["Anothertag", "Atesttag"] == q_document.tags_display

    # Confirm
    q_document = Document.get(Document.id == document.id)
    assert "atesttag|anothertag" == q_document.tags
    assert ["anothertag", "atesttag"] == q_document.tags_split
    assert ["Anothertag", "Atesttag"] == q_document.tags_display

    ############################################################################
    # Test 3 - Query by tag
    ############################################################################
    assert 0 == len(Document.select().where(Document.tags % "*not_in_there*"))
    assert 0 == len(Document.select().where(Document.tags % "*anotherTag*"))
    assert 1 == len(Document.select().where(Document.tags % "*anothertag*"))

    ############################################################################
    # Test 4 - Duplicate tag entry
    ############################################################################
    document.tags_add("AThirdTag")
    document.tags_add("AThirdTag")
    document.save()
    q_document = Document.get(Document.id == document.id)
    assert "anothertag|atesttag|athirdtag" == q_document.tags

    ############################################################################
    # Test 5 - Remove an entry
    ############################################################################
    document.tags_remove("aTestTag")
    document.save()

    # Confirm
    q_document = Document.get(Document.id == document.id)
    assert "anothertag|athirdtag" == q_document.tags


def test_document_dates_cooked(app, document_and_user):
    """Test ability to update json datetimelist field."""
    document, user = document_and_user

    # Setup
    document.save()
    assert not document.dates_cooked

    ############################################################################
    # Test 1 - Single entry
    ############################################################################
    date = datetime(2025, 1, 31)
    document.dates_cooked_add(date)
    document.save()

    # Confirm
    q_document = Document.get(Document.id == document.id)
    date_s = date.strftime("%Y-%m-%d")
    assert date_s == q_document.dates_cooked

    ############################################################################
    # Test 2 - Multiple entries, in sorted order.
    ############################################################################
    date_2 = datetime(2025, 12, 31)
    document.dates_cooked_add(date_2)
    document.save()

    # Confirm
    q_document = Document.get(Document.id == document.id)
    date_2_s = date_2.strftime("%Y-%m-%d")
    assert f"{date_s}|{date_2_s}" == q_document.dates_cooked

    # ############################################################################
    # # Test 3 - Remove an entry
    # ############################################################################
    document.dates_cooked_remove(date)
    document.save()

    # Confirm
    q_document = Document.get(Document.id == document.id)
    assert date_2_s == q_document.dates_cooked
