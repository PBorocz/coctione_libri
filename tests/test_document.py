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


def test_document_listfield_basic(app, document_and_user):
    """Test ability to update json list field."""
    document, user = document_and_user
    # Setup
    document.save()
    assert not document.tags

    ############################################################################
    # Test 1 - Single entry, make sure it's lowercase.
    ############################################################################
    document.tags.append("aTestTag")
    document.save()

    # Confirm
    assert document.updated  # We did a REAL update now!
    q_document = Document.get(Document.id == document.id)
    assert ["atesttag"] == q_document.tags

    ############################################################################
    # Test 2 - Second entry, before current one!
    ############################################################################
    document.tags.append("anothertag")
    document.save()

    # Confirm
    q_document = Document.get(Document.id == document.id)
    assert ["anothertag", "atesttag"] == q_document.tags

    ############################################################################
    # Test 3 - Remove an entry
    ############################################################################
    document.tags.remove("anothertag")
    document.save()

    # Confirm
    q_document = Document.get(Document.id == document.id)
    assert ["atesttag"] == q_document.tags


def test_document_listfield_advanced(app, document_and_user):
    """Test ability to json list field advanced concepts."""
    document, user = document_and_user

    # Setup
    document.save()
    assert not document.tags

    ############################################################################
    # Test 1 - We don't allow duplicates
    ############################################################################
    document.tags.append("atesttag")
    document.tags.append("atesttag")
    document.save()

    # Confirm
    q_document = Document.get(Document.id == document.id)
    assert ["atesttag"] == q_document.tags


def test_document_datetimelistfield(app, document_and_user):
    """Test ability to update json datetimelist field."""
    document, user = document_and_user

    # Setup
    document.save()

    ############################################################################
    # Test 1 - Single entry
    ############################################################################
    now = datetime.now()
    document.dates_cooked.append(now)
    document.save()

    # Confirm
    q_document = Document.get(Document.id == document.id)
    assert [now] == q_document.dates_cooked

    ############################################################################
    # Test 2 - Multiple entries, in sorted order.
    ############################################################################
    time.sleep(0.5)
    now_2 = datetime.now()
    document.dates_cooked.append(now_2)
    document.save()

    # Confirm
    q_document = Document.get(Document.id == document.id)
    assert [now, now_2] == q_document.dates_cooked

    ############################################################################
    # Test 3 - Remove an entry
    ############################################################################
    document.dates_cooked.remove(now)
    document.save()

    # Confirm
    q_document = Document.get(Document.id == document.id)
    assert [now_2] == q_document.dates_cooked
