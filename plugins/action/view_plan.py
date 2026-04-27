# -*- coding: utf-8 -*-
# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.plugins.action import ActionBase


class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        super(ActionModule, self).run(tmp, task_vars)
        # this ensures that we render diffed output (when the plan has a diff)
        # without the need to set diff: True in the task or the --diff flag
        self._task.diff = True
        result = self._execute_module(module_args=self._task.args.copy(), task_vars=task_vars, tmp=tmp)
        return result
