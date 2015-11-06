#!/usr/bin/env python

# 2ping - A bi-directional ping utility
# Copyright (C) 2015 Ryan Finnie
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.

import select
import errno


class EpollPoller():
    poller_type = 'epoll'

    def __init__(self):
        self.poller = select.epoll()
        self.f_dict = {}

    def register(self, f):
        fileno = f.fileno()
        if fileno not in self.f_dict:
            self.poller.register(fileno, select.EPOLLIN)
        self.f_dict[fileno] = f

    def close(self):
        return self.poller.close()

    def poll(self, timeout):
        try:
            poll_res = self.poller.poll(timeout)
        except (select.error, IOError, OSError) as e:
            if e.args[0] not in (errno.EINTR,):
                raise
            return []
        res = []
        for i in poll_res:
            if i[0] in self.f_dict:
                res.append(self.f_dict[i[0]])
        return res


class KqueuePoller():
    poller_type = 'kqueue'

    def __init__(self):
        self.poller = select.kqueue()
        self.kevents = []
        self.f_dict = {}

    def register(self, f):
        fileno = f.fileno()
        if fileno not in self.f_dict:
            self.kevents.append(select.kevent(
                fileno,
                filter=select.KQ_FILTER_READ,
                flags=select.KQ_EV_ADD | select.KQ_EV_ENABLE,
            ))
        self.f_dict[fileno] = f

    def close(self):
        return self.poller.close()

    def poll(self, timeout):
        try:
            poll_res = self.poller.control(self.kevents, 10, timeout)
        except (select.error, IOError, OSError) as e:
            if e.args[0] not in (errno.EINTR,):
                raise
            return []
        res = []
        for i in poll_res:
            if i.ident in self.f_dict:
                res.append(self.f_dict[i.ident])
        return res


class PollPoller():
    poller_type = 'poll'

    def __init__(self):
        self.poller = select.poll()
        self.f_dict = {}

    def register(self, f):
        fileno = f.fileno()
        if fileno not in self.f_dict:
            self.poller.register(fileno, select.POLLIN)
        self.f_dict[fileno] = f

    def close(self):
        return self.poller.close()

    def poll(self, timeout):
        try:
            poll_res = self.poller.poll(timeout * 1000.0)
        except (select.error, IOError, OSError) as e:
            if e.args[0] not in (errno.EINTR,):
                raise
            return []
        res = []
        for i in poll_res:
            if i[0] in self.f_dict:
                res.append(self.f_dict[i[0]])
        return res


class SelectPoller():
    poller_type = 'select'

    def __init__(self):
        self.f_dict = {}

    def register(self, f):
        self.f_dict[f.fileno()] = f

    def close(self):
        pass

    def poll(self, timeout):
        try:
            return select.select(
                self.f_dict.values(),
                [],
                [],
                timeout
            )[0]
        except (select.error, IOError, OSError) as e:
            if e.args[0] not in (errno.EINTR,):
                raise
            return []


def best_poller():
    try:
        return EpollPoller()
    except AttributeError:
        pass
    try:
        return KqueuePoller()
    except AttributeError:
        pass
    try:
        return PollPoller()
    except AttributeError:
        pass
    return SelectPoller()