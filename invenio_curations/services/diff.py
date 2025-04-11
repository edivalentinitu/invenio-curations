# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Graz University of Technology.
#
# Invenio-Curations is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

import ast
import json
from abc import abstractmethod

from invenio_i18n import lazy_gettext as _
from jinja2 import Template

from .utils import HTMLParseException, cleanup_html_tags


class DiffException(Exception):
    pass


class DiffBase:

    @abstractmethod
    def validate_and_cleanup(self): ...

    @abstractmethod
    def compare(self, other): ...

    @abstractmethod
    def from_base_content_object(self, *args): ...

    @abstractmethod
    def get_base_content_object(self, *args): ...

    @abstractmethod
    def to_html(self, *args): ...


class DiffElement(DiffBase):

    def __init__(self, diff=None):
        self._diff = diff

    def __eq__(self, other):
        if not isinstance(other, DiffElement):
            return False
        update_this, key_this, result_this = self._diff
        update_other, key_other, result_other = other.get_diff()

        return (
            update_this == update_other
            and key_this == key_other
            and set(json.dumps(result_this)) == set(json.dumps(result_other))
        )

    def get_diff(self):
        return self._diff

    def match_diff_key(self, diff):
        return isinstance(diff, tuple)

    def compare(self, other):
        """
        Compare method used to compare 2 diffs used to return the difference between the
        state of current instance and the reference represented by other.

        return: False if this instance should be removed from the final list
                True if otherwise
                None if other instance should be added to the final list
        """

        if not isinstance(other, DiffElement):
            return False

        update_this, key_this, result_this = self._diff
        update_other, key_other, result_other = other.get_diff()

        if key_this != key_other:
            return None

        if (
            set(json.dumps(result_this)) == set(json.dumps(result_other))
            and update_this != update_other
            and update_this.lower() != "change"
            and update_other.lower() != "change"
        ):

            # something was reverted
            return False

        elif (
            update_this.lower() == "change"
            and update_other.lower() == "change"
            and key_this == key_other
        ):
            # make sure to set the 'old' values from other
            old_other, _ = result_other
            _, new_this = result_this

            if old_other == new_this:
                # field back to original value, remove from comment
                return False

            result_this = (old_other, new_this)
            self._diff = (update_this, key_this, result_this)
            return True

        elif self._diff == other:
            return False

        else:
            return True

    def from_base_content_object(self, text):
        return ast.literal_eval(text)

    def get_base_content_object(self):
        return str(self.get_diff())

    def to_html(self):
        update, key, result = self._diff
        if update != "change":
            return str({" ".join(key.split(".")): result})
        else:
            old, new = result
            return str({" ".join(key.split(".")): {"old": old, "new": new}})

    def validate_and_cleanup(self):
        _, key, result = self._diff

        return isinstance(key, str) and (
            (isinstance(result, list) and len(result) == 1) or isinstance(result, tuple)
        )


class DiffDescription(DiffElement):

    _name = "metadata.description"

    def match_diff_key(self, diff):
        if not super().match_diff_key(diff):
            return False
        _, key, result = diff
        if isinstance(key, str) and key == self._name:
            return True
        elif (
            isinstance(key, str)
            and isinstance(result, list)
            and len(result) == 1
            and isinstance(result[0], tuple)
        ):
            name, _ = result[0]
            return key + "." + str(name) == self._name

    def validate_and_cleanup(self):
        update, key, result = self._diff
        try:
            if isinstance(result, list) and len(result) == 1:
                field, val = result[0]
                new_val = cleanup_html_tags(val).strip()
                self._diff = (update, key, [(field, new_val)])
                return True

            elif isinstance(result, tuple):
                old, new = result
                new_old = cleanup_html_tags(old).strip()
                new_new = cleanup_html_tags(new).strip()
                self._diff = (update, key, (new_old, new_new))
                return True
            else:
                # not supported yet, don't publish in the comment
                # to not interfere with future diffs
                return False
        except HTMLParseException:
            return False


class DiffProcessor(DiffBase):
    """
    DiffProcessor class. Used to process a list of diffs with the custom implemented behaviour.
    Each diff is an instance of a specific wrapper, defined in _configured_elements.
    """

    _diffs = None
    _configured_elements = None

    _known_actions = {
        "resubmit": _("Record was resubmitted for review with the following changes:"),
        "update_while_critiqued": _(
            "Record started being updated, work in progress..."
        ),
        "update_while_review": _(
            "Record was updated! Please check the latest changes."
        ),
        "default": _("Action triggered comment update"),
    }
    _added = _("Added:")
    _changed = _("Changed:")
    _removed = _("Removed:")

    def __init__(self, diffs=None, configured_elements=None):
        self._diffs = diffs
        self._configured_elements = configured_elements

    def _map_one_diff(self, raw_diff):
        for element in self._configured_elements:
            if element().match_diff_key(raw_diff):
                return element

        return DiffElement

    def map_and_build_diffs(self, raw_diffs):
        if not isinstance(raw_diffs, list):
            return

        self._diffs = []
        for raw_diff in raw_diffs:
            self._diffs.append(self._map_one_diff(raw_diff)(raw_diff))

    def validate_and_cleanup(self):
        to_remove = []

        for diff in self._diffs:
            if not diff.validate_and_cleanup():
                to_remove.append(diff)

        for remove in to_remove:
            self._diffs.remove(remove)

    def from_base_content_object(self, base_content_objects):
        result_diffs = []
        parsed_objects_list = ast.literal_eval(base_content_objects)
        for update in parsed_objects_list:
            df = None
            for element in self._configured_elements:
                try:
                    df = element().from_base_content_object(update)
                    break
                except Exception:
                    continue

            result_diffs.append(self._map_one_diff(df)(df))

        return DiffProcessor(result_diffs, self._configured_elements)

    def get_base_content_object(self):
        result = []
        for diff in self._diffs:
            result.append(diff.get_base_content_object())
        return str(result)

    def to_html(self, action):
        if action not in self._known_actions:
            action = "default"
        template_string = """
<body>
    <h3> {{header}} </h3>

    {% if adds|length > 0 %}
    <h3>{{added_msg}}</h3>
    <ul>
    {% for add in adds %}
        <li>{{add}}</li>
    {% endfor %}
    </ul>
    {% endif %}

    {% if changes|length > 0 %}
    <h3>{{changed_msg}}</h3>
    <ul>
    {% for change in changes %}
        <li>{{change}}</li>
    {% endfor %}
    </ul>
    {% endif %}

    {% if removes|length > 0 %}
    <h3>{{removed_msg}}</h3>
    <ul>
    {% for remove in removes %}
        <li>{{remove}}</li>
    {% endfor %}
    </ul>
    {% endif %}
</body>
        """

        adds = []
        changes = []
        removes = []

        self.validate_and_cleanup()
        for diff in self._diffs:
            update, _, _ = diff.get_diff()
            if update == "add":
                adds.append(diff.to_html())
            elif update == "change":
                changes.append(diff.to_html())
            elif update == "remove":
                removes.append(diff.to_html())

        return Template(template_string).render(
            adds=adds,
            changes=changes,
            removes=removes,
            header=self._known_actions[action],
            added_msg=self._added,
            changed_msg=self._changed,
            removed_msg=self._removed,
        )

    def _get_joined_update(self, update):
        update_name, update_key, result = update.get_diff()

        return "|".join([str(update_name), str(update_key), str(result)])

    def _get_split_update(self, joined_update):
        update_split = joined_update.split("|")
        update_name, update_key = update_split[0], update_split[1]
        update_dict = ast.literal_eval(update_split[2])

        return DiffElement((update_name, update_key, update_dict))

    def compare(self, other):
        if not isinstance(other, DiffProcessor):
            raise DiffException()

        to_add = set()
        to_remove = set()
        skip_second_loop = set()

        self.validate_and_cleanup()
        for diff_this in self._diffs:
            for other_diff in other.get_diffs():
                result = diff_this.compare(other_diff)
                if result is None:
                    continue
                elif not result:
                    to_remove.add(self._get_joined_update(diff_this))
                skip_second_loop.add(self._get_joined_update(other_diff))

        for other_diff in other.get_diffs():
            if self._get_joined_update(other_diff) not in skip_second_loop:
                # keep all operations that were not touched in the previous loop
                to_add.add(self._get_joined_update(other_diff))

        for update in to_add:
            self._diffs.append(self._get_split_update(update))
        for update in to_remove:
            self._diffs.remove(self._get_split_update(update))

        return self

    def get_diffs(self):
        return self._diffs
