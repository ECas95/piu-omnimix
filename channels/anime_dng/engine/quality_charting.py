"""Experimental, deterministic two-foot PIU chart generation on an exact NX grid.

This module changes notes only.  The adapter owns source selection, AUTO provenance,
backups, levels and installation.  No audio analysis or timing quantisation is done.
The ergonomic model deliberately excludes brackets, triples and back-facing crosses;
it is a conservative feasibility model, not a promise of musical quality. Crossed
foot stances are excluded entirely; torso rotation/crossover technique is not modelled.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right, insort
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
from functools import lru_cache
from musical_policy import select_phrases, phrase_preferences, rhythm_audit, spatial_audit
import copy
import hashlib
import math
import random
import pattern_rules
import native_travel

TAP, HEAD, BODY, TAIL = 0x343, 0x357, 0x35B, 0x35F
VERSION = "native-patterns-v5-experimental"
SINGLE = ((-1., -1.), (-1., 1.), (0., 0.), (1., 1.), (1., -1.))
# Panel centers use one panel pitch as a unit. Adjacent 3x3 pads have centers
# three pitches apart: their inner columns are still a full pitch apart.
DOUBLE = tuple((x - 1.5, y) for x, y in SINGLE) + tuple((x + 1.5, y) for x, y in SINGLE)


def grid(nx):
    """Flat (beat, exact source time in ms, split index, row index) tuples."""
    out, beat = [], 0.
    for k, split in enumerate(nx["splits"]):
        h = split["head"]
        start, bpm, rpb = float(h[3]), float(h[4]), int(h[8]) & 255
        if not math.isfinite(start) or not math.isfinite(bpm) or bpm <= 0 or rpb <= 0:
            raise ValueError(f"invalid source timing in split {k}")
        beat += float(h[6]) * bpm / 60000.
        for row in range(len(split["rows"])):
            out.append((beat + row / rpb, start + row * 60000. / bpm / rpb, k, row))
        beat += len(split["rows"]) / rpb
    return out


def _source(nx):
    timeline = grid(nx)
    attacks, opened, repairs = {}, {}, Counter()
    for i, (_, ms, k, r) in enumerate(timeline):
        cells = nx["splits"][k]["rows"][r]
        if cells is None:
            continue
        for lane, value in enumerate(cells):
            kind = value & 255
            if kind in (0x43, 0x57):
                event = attacks.setdefault(i, {"index": i, "beat": timeline[i][0], "ms": ms,
                                               "lanes": [], "holds": []})
                event["lanes"].append(lane)
                if lane in opened:
                    repairs["source_overlapping_hold_as_tap"] += 1
                    opened.pop(lane)
                if kind == 0x57:
                    opened[lane] = i
            elif kind == 0x5F:
                if lane not in opened:
                    repairs["source_orphan_tail_ignored"] += 1
                    continue
                begin = opened.pop(lane)
                if i > begin and ms > timeline[begin][1]:
                    attacks[begin]["holds"].append((i, lane))
                else:
                    repairs["source_nonpositive_hold_as_tap"] += 1
            elif kind == 0x5B and lane not in opened:
                repairs["source_orphan_body_ignored"] += 1
    repairs["source_unclosed_hold_as_tap"] += len(opened)
    events = list(attacks.values())
    last_ms = -math.inf
    for event in events:
        if event["ms"] < last_ms - 1e-7:
            raise ValueError("source attacks run backwards in real time")
        last_ms = event["ms"]
    return timeline, events, dict(repairs)


def notes_of(nx):
    """(beat, ms, source lane, hold end beat/ms or None) for reference/audits."""
    timeline, events, _ = _source(nx)
    notes = []
    for event in events:
        ends = {lane: end for end, lane in event["holds"]}
        for lane in event["lanes"]:
            end = ends.get(lane)
            notes.append((event["beat"], event["ms"], lane,
                          timeline[end][0] if end is not None else None,
                          timeline[end][1] if end is not None else None))
    return notes


def _percent(profile, metric, percentile, fallback, allow_zero=False):
    metrics = profile.get("metrics", profile)
    value = metrics.get(metric)
    if isinstance(value, dict):
        value = value.get(percentile)
    return float(value) if isinstance(value, (int, float)) and (value >= 0 if allow_zero else value > 0) else fallback


def _limits(cols, level, tier, profile):
    p = profile or {}
    row_default = .60 + .35 * min(level, 10) + .29 * max(0, level - 10)
    row_cap = _percent(p, "row_nps", "p90", row_default)
    note_cap = _percent(p, "note_nps", "p90", row_cap * 1.18)
    jump_goal = min(.15, .015 + max(0, level - 2) * .011)
    jump_goal = min(jump_goal, _percent(p, "jump_rows", "p50", jump_goal, allow_zero=True))
    # The original holds define the available vocabulary; this is only a ceiling.
    hold_cap = min(.30, _percent(p, "hold_heads", "p90", .10 + level * .005, allow_zero=True))
    minimum_ms = max(42., 430. / (1. + .42 * max(0, level - 1)))
    limits = {
        "tier": tier, "row_nps_cap": row_cap, "note_nps_cap": note_cap,
        "peak_row_1s_cap": _percent(p, "peak_row_1s", "p90", max(2., row_cap * 1.9)),
        "peak_row_4s_cap": _percent(p, "peak_row_4s", "p75", max(1., row_cap * 1.45)),
        "peak_row_8s_cap": _percent(p, "peak_row_8s", "p75", max(1., row_cap * 1.25)),
        "jump_ratio": jump_goal, "hold_ratio": hold_cap,
        "minimum_interval_ms": minimum_ms, "beam_width": 8,
        "max_facing_degrees": 60., "max_facing_change_degrees": 90.,
        "natural_alternation_gap_ms": 650.,
        "rapid_jack_ratio_cap": _percent(p, "rapid_jacks", "p90", .08, allow_zero=True),
        "travel_speed": 5. + level * .10,
        "stance_span": 2.9 if cols == 5 else 3.05,
        "max_jump_span": 2.9 if cols == 5 else 3.05,
    }
    limits['travel_speed'],limits['travel_model_reference']=native_travel.speed(cols,level)
    for key in limits:
        if isinstance(p.get(key), (int, float)):
            limits[key] = float(p[key])
    limits["jump_ratio"] = max(0., min(.25, limits["jump_ratio"]))
    limits["hold_ratio"] = max(0., min(.40, limits["hold_ratio"]))
    limits["beam_width"] = max(2, min(24, int(limits["beam_width"])))
    return limits


def _stable(seed, *items):
    raw = (str(seed) + ":" + repr(items)).encode()
    return int.from_bytes(hashlib.blake2s(raw, digest_size=8).digest(), "little") / 2**64


def _accent(event, phase_frequency, seed, level):
    phase = round(event["beat"] % 8., 5)
    beat_fraction = event["beat"] % 1.
    integer = min(beat_fraction, 1. - beat_fraction) < 1e-5
    half = abs(beat_fraction - .5) < 1e-5
    quarter = min(abs(beat_fraction - .25), abs(beat_fraction - .75)) < 1e-5
    metric = 2.7 if integer else 1.55 if half else .85 if quarter else .40
    if level > 10:
        metric = 1.8 if integer else 1.5 if half else 1.1 if quarter else .70
    return (metric + (.6 if phase < 1e-5 else 0.) + .30 * min(2, len(event["lanes"]))
            + (.35 if event["holds"] else 0.) + .2 * phase_frequency[phase]
            + .12 * _stable(seed, phase))


def _burst_allowed(times, ms, limits):
    for window in (1, 4, 8):
        cap = max(1, math.floor(limits[f"peak_row_{window}s_cap"] * window + 1e-8))
        # All existing windows that would include the insertion, not just the past.
        lo, hi = bisect_right(times, ms - window * 1000.), bisect_left(times, ms + window * 1000.)
        local = times[lo:hi]
        insort(local, ms)
        left = 0
        for right, now in enumerate(local):
            while now - local[left] >= window * 1000. - 1e-7:
                left += 1
            if right - left + 1 > cap:
                return False
    return True


def _select(events, target, limits, seed, level):
    if not events or target <= 0:
        return [], 0
    span = max(1., (events[-1]["ms"] - events[0]["ms"]) / 1000.)
    effective = min(int(target), max(1, int(span * limits["note_nps_cap"])))
    want = min(len(events), round(effective / (1. + limits["jump_ratio"])),
               max(1, int(span * limits["row_nps_cap"])))
    phrases = defaultdict(list)
    phase_frequency = Counter(round(e["beat"] % 8., 5) for e in events)
    largest = max(phase_frequency.values())
    phase_frequency = {phase: frequency / largest for phase, frequency in phase_frequency.items()}
    for event in events:
        phrases[int(event["beat"] // 8)].append(event)
    weights = {phrase: len(group) ** .90 for phrase, group in phrases.items()}
    total_weight = sum(weights.values())
    quota = {phrase: min(len(phrases[phrase]), int(want * weight / total_weight))
             for phrase, weight in weights.items()}
    remaining = want - sum(quota.values())
    priority = sorted(phrases, key=lambda q: (-(want * weights[q] / total_weight - quota[q]), q))
    while remaining:
        progressed = False
        for phrase in priority:
            if quota[phrase] < len(phrases[phrase]):
                quota[phrase] += 1
                remaining -= 1
                progressed = True
                if not remaining:
                    break
        if not progressed:
            break
    times, chosen = [], []
    for phrase in sorted(phrases):
        if quota[phrase] == 0:
            continue
        ranked = sorted(phrases[phrase], key=lambda e: (-_accent(e, phase_frequency, seed, level), e["index"]))
        accepted = 0
        for event in ranked:
            pos = bisect_left(times, event["ms"])
            gap = limits["minimum_interval_ms"]
            if ((pos and event["ms"] - times[pos - 1] < gap - 1e-7)
                    or (pos < len(times) and times[pos] - event["ms"] < gap - 1e-7)):
                continue
            if not _burst_allowed(times, event["ms"], limits):
                continue
            insort(times, event["ms"])
            chosen.append(event)
            accepted += 1
            if accepted >= quota[phrase]:
                break
    return sorted(chosen, key=lambda e: e["index"]), effective


def _motif_preferences(events, cols, motifs, seed):
    pool = [m for m in (motifs or []) if len(m.get("lanes", [])) == 4
            and len(m.get("gaps", [])) == 3 and all(0 <= int(l) < cols for l in m["lanes"])]
    if not pool:
        # Alternating non-crossing vocabulary; geometry still checks every entrance.
        lanes = [0, 4, 1, 3, 2, 4, 0, 3] if cols == 5 else [0, 4, 2, 3, 5, 6, 7, 9, 6, 8, 7, 5, 3, 4, 2, 1]
        return [lanes[(i + int(seed) % len(lanes)) % len(lanes)] for i in range(len(events))], 0
    pool.sort(key=lambda m: (-int(m.get("count", 1)), tuple(m["lanes"])))
    indexed = defaultdict(list)
    for motif in pool:
        indexed[tuple(round(float(g), 3) for g in motif["gaps"])].append(motif)
    preferred, used, cache = [], 0, {}
    rng = random.Random(seed)
    for begin in range(0, len(events), 4):
        block = events[begin:begin + 4]
        if len(block) < 4:
            preferred.extend([None] * len(block))
            continue
        gaps = tuple(round(block[i + 1]["beat"] - block[i]["beat"], 3) for i in range(3))
        choices = indexed.get(gaps)
        if not choices:
            choices = sorted(pool[:80], key=lambda m: sum(abs(float(a) - b) for a, b in zip(m["gaps"], gaps)))[:8]
        # Repeated rhythm phrases retain an identity; variations alter its entrance.
        identity = (gaps, int(block[0]["beat"] % 8 * 4))
        if identity not in cache:
            motif = rng.choices(choices[:24], weights=[max(1, int(m.get("count", 1))) for m in choices[:24]])[0]
            mirror = bool(rng.getrandbits(1))
            cache[identity] = [cols - 1 - int(l) if mirror else int(l) for l in motif["lanes"]]
        preferred.extend(cache[identity])
        used += 1
    return preferred, used


@dataclass(slots=True)
class _Node:
    previous: object
    index: int
    actions: tuple
    repair: str | None = None
    setups: tuple = ()


@dataclass(slots=True)
class _State:
    positions: tuple
    times: tuple
    holds: tuple
    last_foot: int
    last_lanes: tuple
    last_ms: float
    history: tuple
    cost: float
    node: object
    hold_history: tuple = ()
    stream_history: tuple = ()
    release_history: tuple = ()


def _distance(a, b, coords):
    xa, ya = coords[a]
    xb, yb = coords[b]
    return math.hypot(xa - xb, ya - yb)


def _released(state, index, timeline):
    holds, times = list(state.holds), list(state.times)
    for foot, end in enumerate(holds):
        if end >= 0 and end < index:
            times[foot] = max(times[foot], timeline[end][1])
            holds[foot] = -1
    return tuple(holds), tuple(times)


def _travel_allowed(a, b, dt, coords, limits):
    if dt < -1e-7:
        return False
    return _distance(a, b, coords) <= .75 + limits["travel_speed"] * max(0., dt) / 1000. + 1e-7


def facing(positions, coords):
    left, right = (coords[p] for p in positions)
    dx, dy = right[0] - left[0], right[1] - left[1]
    return math.degrees(math.atan2(-dy, dx))


def forward(positions, coords, limits):
    return positions[0] != positions[1] and abs(facing(positions, coords)) <= limits.get("max_facing_degrees", 60.) + 1e-7


@lru_cache(maxsize=16384)
def _anchor_future_possible(anchor_foot,anchor_lane,mobile_lane,mobile_ms,future,coords,speed,span,angle):
    # While one foot is pinned, every upcoming source attack must have a route
    # for the mobile foot. Center anchors can strand it on a two-panel vertical
    # edge whose travel is too long at eighth/sixteenth-note speed (user image7).
    if not future:return True
    limits={'travel_speed':speed,'max_facing_degrees':angle}
    reachable={mobile_lane};previous=mobile_ms
    for ms in future:
        next_lanes=set()
        for old in reachable:
            for lane in range(len(coords)):
                if lane==anchor_lane or (lane==old and ms-previous<300.-1e-7):continue
                positions=(anchor_lane,lane) if anchor_foot==0 else (lane,anchor_lane)
                if not forward(positions,coords,limits):continue
                if coords[positions[0]][0]>coords[positions[1]][0]+.01:continue
                if _distance(*positions,coords)>span+1e-7:continue
                if _travel_allowed(old,lane,ms-previous,coords,limits):next_lanes.add(lane)
        if not next_lanes:return False
        reachable=next_lanes;previous=ms
    return True


def _recent_releases(state,index,timeline):
    beat,ms,_,_=timeline[index];releases=list(state.release_history)
    for foot,end in enumerate(state.holds):
        if end>=0 and end<index:releases.append((state.positions[foot],timeline[end][1],timeline[end][0],foot))
    return tuple(v for v in releases if 0<=ms-v[1]<=350.+1e-5 and 0<=beat-v[2]<=.50001)

def _post_hold_continuation(state,foot,releases):
    # The foot that was already mobile may finish the phrase while the freshly
    # released foot recovers. It must still pass real travel/facing/stance checks,
    # and may never retap the panel that just ended the hold.
    return any(len(v)>3 and v[3]!=foot and state.times[v[3]]<=v[1]+1e-5 for v in releases)


def _expand(state, event, count, ends, preferred, coords, limits, timeline, repair=None, setups=None):
    index, ms = event["index"], event["ms"]
    if count == 2 and len(ends) == 1:
        # A jump can anchor either foot. Slot zero previously forced all such
        # holds onto the left foot, recreating the same direction repeatedly.
        return (_expand(state,event,count,(ends[0],-1),preferred,coords,limits,timeline,repair,setups)
                + _expand(state,event,count,(-1,ends[0]),preferred,coords,limits,timeline,repair,setups))
    holds, times = _released(state, index, timeline)
    releases=_recent_releases(state,index,timeline)
    if setups is None:
        expanded = _expand(state, event, count, ends, preferred, coords, limits, timeline, repair, ())
        # A player may reposition between musical phrases. Record and replay those
        # silent moves explicitly; recovery cannot move a held foot or teleport.
        if ms - state.last_ms >= 900. and all(end < 0 for end in holds):
            postures = ((0, 4), (1, 3)) if len(coords) == 5 else ((0, 4), (3, 6), (5, 9))
            setup_ms = ms - 250.
            for posture in postures:
                if posture == state.positions:
                    continue
                if all(_travel_allowed(state.positions[f], posture[f], setup_ms - times[f], coords, limits)
                       for f in (0, 1)):
                    moves = tuple((f, posture[f], setup_ms) for f in (0, 1) if posture[f] != state.positions[f])
                    penalty = sum(_distance(state.positions[f], posture[f], coords) for f in (0, 1)) * .30
                    recovered_times = tuple(setup_ms if posture[f] != state.positions[f] else times[f]
                                            for f in (0, 1))
                    recovered = _State(posture, recovered_times, holds, state.last_foot,
                                       state.last_lanes, state.last_ms, state.history, state.cost + penalty, state.node, state.hold_history, state.stream_history, releases)
                    expanded.extend(_expand(recovered, event, count, ends, preferred, coords, limits, timeline,
                                            repair, moves))
        return expanded
    free = [foot for foot in (0, 1) if holds[foot] < 0]
    if len(free) < count:
        return []
    cols = len(coords)
    possibilities = []
    if count == 1:
        possibilities = [((foot, lane),) for foot in free for lane in range(cols)]
    else:
        possibilities = [((0, left), (1, right)) for left, right in combinations(range(cols), 2)
                         if coords[left][0] <= coords[right][0] + .01
                         and _distance(left, right, coords) <= limits["max_jump_span"] + 1e-7]
    result = []
    for steps in possibilities:
        lanes = tuple(lane for _, lane in steps)
        if any(pattern_rules.release_violation(releases,lane,event['beat'],ms) for lane in lanes):continue
        if lanes == state.last_lanes and ms - state.last_ms < 300. - 1e-7:
            continue  # Involuntary rapid same-panel repetitions are never generated.
        positions, next_times, next_holds = list(state.positions), list(times), list(holds)
        penalty = 0.
        for foot, lane in steps:
            other = 1 - foot
            if holds[other] >= 0 and lane == positions[other]:
                break
            dt = ms - times[foot]
            if not _travel_allowed(positions[foot], lane, dt, coords, limits):
                break
            travel = _distance(positions[foot], lane, coords)
            penalty += .25 * travel * travel / max(.30, min(1.5, dt / 400.))
            positions[foot], next_times[foot] = lane, ms
        else:
            if positions[0] == positions[1] or coords[positions[0]][0] > coords[positions[1]][0] + .01:
                continue
            if _distance(positions[0], positions[1], coords) > limits["stance_span"] + 1e-7:
                continue
            if not forward(positions, coords, limits):
                continue
            if (not setups and ms - state.last_ms < 900.
                    and abs(facing(positions, coords) - facing(state.positions, coords)) > limits["max_facing_change_degrees"] + 1e-7):
                continue
            explicit_jack = count == 1 and lanes == state.last_lanes and ms-state.last_ms >= 300.
            if (count == 1 and len(free) == 2 and state.last_foot == steps[0][0]
                    and ms - state.last_ms < limits["natural_alternation_gap_ms"] and not setups and not explicit_jack and not _post_hold_continuation(state,steps[0][0],releases)):
                continue
            penalty += .012 * abs(facing(positions, coords) - facing(state.positions, coords))
            if preferred is not None:
                penalty += 9. * min(_distance(lane, preferred, coords) for lane in lanes)
            if count == 1:
                penalty += 1.1 * state.history.count(lanes[0])
            if len(state.history) >= 6 and count == 1:
                h = state.history
                if h[-4:] == h[-6:-2] and lanes[0] == h[-2]:
                    penalty += 12.  # Reject a cheap repeated shuffle even when travel is short.
            actions = []
            local_repair = repair
            for slot, (foot, lane) in enumerate(steps):
                end = ends[slot] if slot < len(ends) else -1
                if (end >= 0 and next_holds[1 - foot] >= 0
                        and event.get("next_index", math.inf) <= min(end, next_holds[1 - foot])):
                    end = -1
                    local_repair = "hold_reduced_to_preserve_following_rhythm"
                if end >= 0:
                    next_holds[foot] = end
                actions.append((lane, foot, end))
            if repair:
                penalty += 20.
            hold_history=state.hold_history;stream_history=state.stream_history;bad=False
            for lane,foot,end in actions:
                if end>=0:
                    if pattern_rules.hold_violation(hold_history,lane,foot,ms,len(free)==2,bool(hold_history and state.last_ms==hold_history[3])):bad=True;break
                    if hold_history and ms-hold_history[2]<=650 and foot==hold_history[1]:penalty+=4.
                    mobile=1-foot
                    mobile_time=next_times[mobile]
                    if next_holds[mobile]>=0:mobile_time=max(mobile_time,timeline[next_holds[mobile]][1])
                    future=event.get('hold_future',())
                    if not _anchor_future_possible(foot,lane,positions[mobile],mobile_time,future,coords,
                                                  limits['travel_speed'],limits['stance_span'],limits['max_facing_degrees']):bad=True;break
                    hold_history=(lane,foot,timeline[end][1],ms)
            if bad:continue
            if count==1 and all(end<0 for end in next_holds):
                lane=lanes[0]
                if pattern_rules.stream_violation(stream_history,lane,event['beat'],ms):continue
                stream_history=pattern_rules.next_stream(stream_history,lane,event['beat'],ms)
            else:stream_history=()
            history = (state.history + lanes)[-16:]
            result.append(_State(tuple(positions), tuple(next_times), tuple(next_holds),
                                 steps[0][0] if count == 1 else 2, lanes, ms, history,
                                 state.cost + penalty,
                                 _Node(state.node, index, tuple(actions), local_repair, setups),hold_history,stream_history,releases))
    return result


def _assign(events, timeline, cols, limits, preferred, seed):
    if not events:
        return [], {}
    if cols == 10:
        limits["double_start_beat"] = events[0]["beat"]
        limits["double_phrase_beats"] = min(8., max(.5, (events[-1]["beat"] - events[0]["beat"]) / 6.))
    coords = SINGLE if cols == 5 else DOUBLE
    positions = (0, 4) if cols == 5 else (3, 6)
    start = events[0]["ms"] - 2000.
    states = [_State(positions, (start, start), (-1, -1), -1, (), -math.inf, (), 0., None)]
    jump_count = min(round(len(events) * limits["jump_ratio"]),
                     max(0, int(limits.get("note_budget", math.inf)) - len(events))
                     if "note_budget" in limits else len(events))
    jump_rank = sorted(range(len(events)), key=lambda i: (
        -(1. if min(events[i]["beat"] % 1., 1 - events[i]["beat"] % 1.) < 1e-5 else 0.),
        -min(2, len(events[i]["lanes"])), _stable(seed, "jump", events[i]["beat"] % 8), i))
    jumps = set(jump_rank[:jump_count])
    hold_budget = math.floor((len(events) + jump_count) * limits["hold_ratio"])
    held = 0
    for i, event in enumerate(events):
        event = {**event, "next_index": events[i + 1]["index"] if i + 1 < len(events) else math.inf}
        count = 2 if i in jumps else 1
        hold_options = sorted(event["holds"], key=lambda pair: (pair[0], pair[1]))
        end = next((end for end, _ in hold_options
                    if end > event["index"] and timeline[end][1] - event["ms"] >= 180.), -1)
        ends = (end,) if end >= 0 and held < hold_budget else ()
        if ends:
            # One anchored foot leaves only one mobile foot. Very dense alternating
            # source rhythms cannot be remapped into impossible one-foot sprints.
            hop_ms = (math.sqrt(2.) - .75) / limits["travel_speed"] * 1000.
            following = [event] + [future for future in events[i + 1:]
                                   if future["index"] <= ends[0]]
            if any(b["ms"] - a["ms"] < hop_ms - 1e-7 for a, b in zip(following, following[1:])):
                ends = ()
        if ends:
            # The tail panel remains unavailable briefly after release. Plan the
            # mobile foot through that recovery window as well, rather than
            # accepting an anchor whose next attack would have no legal panel.
            # A rejected hold is explicitly reduced to a tap; its attack stays.
            tail_beat,tail_ms,_,_=timeline[ends[0]]
            event['hold_future']=tuple(future['ms'] for future in events[i+1:]
                if future['index']<=ends[0] or
                (future['ms']-tail_ms<=350.+1e-5 and future['beat']-tail_beat<=.50001))
        held += bool(ends)
        expanded = []
        for state in states:
            expanded.extend(_expand(state, event, count, ends, preferred[i], coords, limits, timeline))
        if not expanded and count == 2:
            for state in states:
                expanded.extend(_expand(state, event, 1, ends, preferred[i], coords, limits, timeline,
                                        "jump_reduced_for_feet"))
        if not expanded and ends:
            for state in states:
                expanded.extend(_expand(state, event, 1, (), preferred[i], coords, limits, timeline,
                                        "hold_reduced_for_feet"))
        if not expanded:
            # Explicitly report a rhythm omission rather than overwrite a held cell.
            expanded = [_State(s.positions, s.times, s.holds, s.last_foot, s.last_lanes, s.last_ms,
                               s.history, s.cost + 80., _Node(s.node, event["index"], (), "onset_omitted_for_feet"),s.hold_history,s.stream_history,s.release_history)
                        for s in states]
        unique = {}
        for state in sorted(expanded, key=lambda s: (s.cost, s.positions, s.holds, s.last_foot)):
            key = (state.positions, state.holds, state.last_foot, state.last_lanes, state.history[-4:],state.hold_history,state.stream_history[-4:],state.release_history)
            if key not in unique:
                unique[key] = state
        states = list(unique.values())[:limits["beam_width"]]
    node = min(states, key=lambda s: (s.cost, s.positions)).node
    plan, repairs = [], Counter()
    while node is not None:
        if node.repair:
            repairs[node.repair] += 1
        if node.actions:
            record = {"index": node.index, "actions": [list(action) for action in node.actions]}
            if node.setups:
                record["setups"] = [list(setup) for setup in node.setups]
            plan.append(record)
        node = node.previous
    return list(reversed(plan)), dict(repairs)


def _render(source, cols, level, timeline, plan):
    nx = copy.deepcopy(source)
    nx["cols"] = cols
    nx.setdefault("unk", 0)
    nx.setdefault("pool", b"")
    nx["tags"] = [(key, value) for key, value in nx.get("tags", []) if key not in (1000, 1001)] + [(1000, 1), (1001, int(level))]
    flat = [[0] * cols for _ in timeline]
    for event in plan:
        index = event["index"]
        for lane, _, end in event["actions"]:
            if flat[index][lane]:
                raise ValueError("internal generator attempted a cell overwrite")
            if end < 0:
                flat[index][lane] = TAP
            else:
                if any(flat[row][lane] for row in range(index, end + 1)):
                    raise ValueError("internal generator attempted a hold overlap")
                flat[index][lane] = HEAD
                for row in range(index + 1, end):
                    flat[row][lane] = BODY
                flat[end][lane] = TAIL
    for row, (_, _, k, r) in zip(flat, timeline):
        nx["splits"][k]["rows"][r] = tuple(row) if any(row) else None
    return nx


def _peak(times, window):
    left, best = 0, 0
    for right, now in enumerate(times):
        while now - times[left] >= window * 1000. - 1e-7:
            left += 1
        best = max(best, right - left + 1)
    return best / window


def validate(nx, source_nx=None, footsteps=None, limits=None):
    """Recheck serialized/parsed NX data; optional plan proves two-foot feasibility."""
    timing_reference_provided = source_nx is not None
    source_nx = nx if source_nx is None else source_nx
    timeline, source_events, _ = _source(source_nx)
    errors = []
    cols = nx["cols"]
    if cols not in (5, 10):
        errors.append("unsupported output columns")
    if len(nx["splits"]) != len(source_nx["splits"]):
        errors.append("split count changed")
    for k, (out, original) in enumerate(zip(nx["splits"], source_nx["splits"])):
        if tuple(out["head"]) != tuple(original["head"]) or len(out["rows"]) != len(original["rows"]):
            errors.append(f"split timing/grid changed: {k}")
    source_onsets = {event["index"] for event in source_events}
    source_holds = {(event["index"], end) for event in source_events for end, _ in event["holds"]}
    opened, attack_map, hold_pairs = {}, {}, set()
    times, notes, heads, contact_max, jumps, rapid_repeats, rapid_lane_revisits = [], 0, 0, 0, 0, 0, 0
    rapid_single_transitions, rapid_single_jacks = 0, 0
    previous_single = None
    previous_lane_time = {}
    last_lanes, last_time = (), -math.inf
    lane_counts = Counter()
    for index, (_, ms, k, r) in enumerate(timeline):
        try:
            row = nx["splits"][k]["rows"][r]
        except IndexError:
            errors.append("missing output row")
            break
        if row is None:
            if opened:
                errors.append(f"missing hold body at row {index}")
            continue
        if len(row) != cols:
            errors.append(f"wrong column count at row {index}")
            continue
        contacts, lanes = 0, []
        for lane, value in enumerate(row):
            kind = value & 255
            if kind in (0, 0x80):
                if lane in opened:
                    errors.append(f"missing hold body at row {index} lane {lane}")
                continue
            contacts += 1
            if kind in (0x43, 0x57):
                if index not in source_onsets:
                    errors.append(f"attack outside source onset at row {index}")
                if lane in opened:
                    errors.append(f"attack overwrites hold at row {index} lane {lane}")
                lanes.append(lane)
                lane_counts[lane] += 1
                if ms - previous_lane_time.get(lane, -math.inf) < 250. - 1e-7:
                    rapid_lane_revisits += 1
                previous_lane_time[lane] = ms
                notes += 1
                if kind == 0x57:
                    opened[lane] = index
                    heads += 1
            elif kind == 0x5B:
                if lane not in opened:
                    errors.append(f"orphan hold body at row {index} lane {lane}")
            elif kind == 0x5F:
                if lane not in opened:
                    errors.append(f"orphan hold tail at row {index} lane {lane}")
                else:
                    pair = (opened.pop(lane), index)
                    hold_pairs.add(pair)
                    if pair not in source_holds:
                        errors.append(f"hold duration outside source at row {index} lane {lane}")
            else:
                errors.append(f"unexpected generated cell kind {kind}")
        contact_max = max(contact_max, contacts)
        if contacts > 2:
            errors.append(f"more than two contacts at row {index}")
        if lanes:
            lanes = tuple(lanes)
            if lanes == last_lanes and ms - last_time < 300. - 1e-7:
                rapid_repeats += 1
                errors.append(f"rapid identical row at {index}")
            if len(lanes) == 1:
                if previous_single is not None and 0 < ms - previous_single[1] <= 250. + 1e-7:
                    rapid_single_transitions += 1
                    rapid_single_jacks += lanes[0] == previous_single[0]
                previous_single = (lanes[0], ms)
            last_lanes, last_time = lanes, ms
            attack_map[index] = lanes
            times.append(ms)
            jumps += len(lanes) == 2
    if opened:
        errors.append("unclosed generated holds")
    level = next((value for key, value in nx.get("tags", []) if key == 1001), 1)
    actual_limits = limits or _limits(cols, int(level), "", None)
    max_travel, alternations, same_foot, double_cross = 0., 0, 0, 0
    max_required_speed=0.
    max_facing = 0.; unsupported_doublesteps = 0; post_hold_continuations=0
    if footsteps is not None:
        coords = SINGLE if cols == 5 else DOUBLE
        positions = (0, 4) if cols == 5 else (3, 6)
        start = times[0] - 2000. if times else 0.
        state = _State(positions, (start, start), (-1, -1), -1, (), -math.inf, (), 0., None)
        seen = set()
        for step in footsteps:
            index = step["index"]
            if index not in attack_map:
                errors.append("foot plan contains missing attack")
                continue
            seen.add(index)
            ms = timeline[index][1]
            actions = step["actions"]
            if tuple(sorted(action[0] for action in actions)) != tuple(sorted(attack_map[index])):
                errors.append(f"foot plan mismatch at {index}")
            feet = [action[1] for action in actions]
            if len(set(feet)) != len(feet) or any(foot not in (0, 1) for foot in feet):
                errors.append(f"invalid simultaneous foot allocation at {index}")
                continue
            holds, foot_times = _released(state, index, timeline)
            releases=_recent_releases(state,index,timeline)
            positions, foot_times, holds = list(state.positions), list(foot_times), list(holds)
            for foot, lane, setup_ms in step.get("setups", []):
                if foot not in (0, 1) or lane not in range(cols):
                    errors.append(f"invalid silent reposition at {index}")
                    continue
                if holds[foot] >= 0 or setup_ms > ms:
                    errors.append(f"held/late silent reposition at {index}")
                if not _travel_allowed(positions[foot], lane, setup_ms - foot_times[foot], coords, actual_limits):
                    errors.append(f"impossible silent reposition at {index}")
                positions[foot], foot_times[foot] = lane, setup_ms
            for lane, foot, end in actions:
                if holds[foot] >= 0:
                    errors.append(f"held foot reused at {index}")
                if not _travel_allowed(positions[foot], lane, ms - foot_times[foot], coords, actual_limits):
                    errors.append(f"impossible foot travel at {index}")
                travel = _distance(positions[foot], lane, coords)
                max_travel = max(max_travel, travel)
                dt=ms-foot_times[foot]
                if dt>1e-7:max_required_speed=max(max_required_speed,max(0.,travel-.75)/(dt/1000.))
                if cols == 10 and positions[foot] // 5 != lane // 5:
                    double_cross += 1
                positions[foot], foot_times[foot], holds[foot] = lane, ms, end
                row = nx["splits"][timeline[index][2]]["rows"][timeline[index][3]]
                if ((row[lane] & 255) == 0x57) != (end >= 0):
                    errors.append(f"foot hold allocation mismatch at {index}")
                if end >= 0 and (index, end) not in hold_pairs:
                    errors.append(f"foot hold tail mismatch at {index}")
            angle = facing(positions, coords)
            max_facing = max(max_facing, abs(angle))
            if not forward(positions, coords, actual_limits):
                errors.append(f"sideways/back-facing stance at {index}")
            if (not step.get("setups") and ms - state.last_ms < 900.
                    and abs(angle-facing(state.positions, coords)) > actual_limits.get("max_facing_change_degrees",90.) + 1e-7):
                errors.append(f"abrupt facing change at {index}")
            released_before, _ = _released(state, index, timeline)
            if (len(actions) == 1 and actions[0][1] == state.last_foot
                    and all(h < 0 for h in released_before) and not step.get("setups")
                    and ms-state.last_ms < actual_limits.get("natural_alternation_gap_ms",650.)
                    and not (attack_map[index]==state.last_lanes and ms-state.last_ms>=300.)
                    and not _post_hold_continuation(state,actions[0][1],releases)):
                unsupported_doublesteps += 1
                errors.append(f"unprepared same-foot transition at {index}")
            if coords[positions[0]][0] > coords[positions[1]][0] + .01:
                errors.append(f"crossed-foot stance excluded at {index}")
            if _distance(positions[0], positions[1], coords) > actual_limits["stance_span"] + 1e-7:
                errors.append(f"impossible stance width at {index}")
            if len(actions) == 2 and _distance(actions[0][0], actions[1][0], coords) > actual_limits["max_jump_span"] + 1e-7:
                errors.append(f"wide jump at {index}")
            if len(actions)==1 and actions[0][1]==state.last_foot and _post_hold_continuation(state,actions[0][1],releases):post_hold_continuations+=1
            foot = feet[0] if len(feet) == 1 else 2
            if foot < 2 and 0 <= state.last_foot < 2:
                if foot == state.last_foot:
                    same_foot += 1
                else:
                    alternations += 1
            state = _State(tuple(positions), tuple(foot_times), tuple(holds), foot, attack_map[index], ms,
                           (), 0., None,(),(),releases)
        if seen != set(attack_map):
            errors.append("foot plan does not cover all attacks")
    span = max(1., (source_events[-1]["ms"] - source_events[0]["ms"]) / 1000.) if source_events else 1.
    measurements = {"notes": notes, "rows": len(times), "holds": heads, "span_s": span,
                    "note_nps": notes / span, "row_nps": len(times) / span,
                    "jump_rows": jumps / max(1, len(times)), "hold_heads": heads / max(1, notes),
                    "peak_row_1s": _peak(times, 1), "peak_row_4s": _peak(times, 4), "peak_row_8s": _peak(times, 8),
                    "contact_max": contact_max, "rapid_identical_rows": rapid_repeats,
                    "rapid_jacks": rapid_single_jacks / max(1, rapid_single_transitions),
                    "rapid_single_transitions": rapid_single_transitions,
                    "rapid_lane_revisit_ratio": rapid_lane_revisits / max(1, notes),
                    "lane_counts": dict(sorted(lane_counts.items())), "max_foot_travel": max_travel,"max_required_travel_speed":max_required_speed,
                    "pad_note_counts": [sum(n for lane, n in lane_counts.items() if lane // 5 == pad)
                                        for pad in range(cols // 5)],
                    "alternating_single_transitions": alternations, "same_foot_single_transitions": same_foot,
                    "double_foot_pad_transitions": double_cross,
                    "max_facing_degrees":max_facing,"unsupported_doublesteps":unsupported_doublesteps,"supported_post_hold_continuations":post_hold_continuations}
    if limits is not None:
        for name in ("row_nps", "note_nps", "peak_row_1s", "peak_row_4s", "peak_row_8s"):
            # One event of tolerance only for very short charts / the integer budget.
            tolerance = 1. / span if name in ("row_nps", "note_nps") else 1e-6
            if measurements[name] > limits[name + "_cap"] + tolerance:
                errors.append(f"official profile cap exceeded: {name}")
        if measurements["rapid_jacks"] > limits.get("rapid_jack_ratio_cap", 1.) + 1e-7:
            errors.append("official profile cap exceeded: rapid_jacks")
    pattern_check=pattern_rules.audit(timeline,_source(nx)[1],footsteps) if footsteps is not None else None
    if pattern_check and not pattern_check['pass']:
        errors.extend('pattern rule '+e['kind']+' at '+str(e['index']) for e in pattern_check['errors'])
    return {"pattern_rules":pattern_check,"pass": not errors, "errors": errors,
            "timing_reference_provided": timing_reference_provided,
            "foot_plan_replayed": footsteps is not None, **measurements}


def generate(source_nx: dict, cols: int, level: int, tier: str, target_notes: int,
             profile: dict | None = None, motifs: list | None = None, seed: int = 0):
    """Return an NX dictionary and reproducible metrics, including a foot-plan proof.

    Attack count is a goal bounded by reference/profile/ergonomic constraints.  Lost
    density and repairs are reported; source onsets or timing are never invented.
    ``profile`` is one entry from official_profiles.json (metrics percentile dicts),
    optionally with flat explicit *_cap overrides. ``motifs`` is its mode/level list.
    """
    if cols not in (5, 10) or not 1 <= int(level) <= 28:
        raise ValueError("only Single/Double levels 1..28 are supported")
    if target_notes < 1:
        raise ValueError("a playable generation needs a positive attack target")
    timeline, source_events, source_repairs = _source(source_nx)
    if not source_events:
        raise ValueError("source has no playable attacks")
    limits = _limits(cols, int(level), tier, profile)
    selected, effective_target = select_phrases(source_events, int(target_notes), limits, int(seed), int(level))
    limits["note_budget"] = effective_target
    preferred, motif_count = phrase_preferences(selected, cols, motifs, int(seed))
    plan, repairs = _assign(selected, timeline, cols, limits, preferred, int(seed))
    if len(selected) - len(plan) > max(1, int(.02 * len(selected))) and limits["hold_ratio"] > 0:
        trial_limits = {**limits, "hold_ratio": 0.}
        trial, trial_repairs = _assign(selected, timeline, cols, trial_limits, preferred, int(seed))
        if len(trial) > len(plan):
            repairs = {**trial_repairs, "hold_policy_relaxed_to_preserve_rhythm": 1}
            plan = trial
    output = _render(source_nx, cols, level, timeline, plan)
    # Validate after NX encoding/decoding, not merely the planned event objects.
    import nx20
    encoded = nx20.build(output)
    decoded = nx20.parse(encoded)
    verification = validate(decoded, source_nx, plan, limits)
    if "official profile cap exceeded: rapid_jacks" in verification["errors"] and limits["jump_ratio"] > 0:
        # Removing a jump must not hide an unintended A / jump / A jack when
        # the official comparison measures adjacent *single* rows.
        trial_limits = {**limits, "jump_ratio": 0.}
        plan, repairs = _assign(selected, timeline, cols, trial_limits, preferred, int(seed))
        repairs["jumps_reduced_to_avoid_single_row_jacks"] = 1
        output = _render(source_nx, cols, level, timeline, plan)
        encoded = nx20.build(output)
        decoded = nx20.parse(encoded)
        verification = validate(decoded, source_nx, plan, limits)
    if not verification["pass"]:
        raise ValueError("generated chart failed post-write validation: " + "; ".join(verification["errors"][:12]))
    if not verification["notes"]:
        raise ValueError("ergonomic constraints produced an empty chart")
    omission_ratio = (len(selected) - len(plan)) / max(1, len(selected))
    if omission_ratio > .05:
        raise ValueError(f"foot constraints omitted {omission_ratio:.1%} of selected rhythm (maximum 5%)")
    if cols == 10 and len(plan) >= 8 and verification["span_s"] >= 3. and min(verification["pad_note_counts"]) == 0:
        raise ValueError("Double generation failed to use both pads")
    by_index = {record["index"]: record for record in plan}
    matched = sum(preferred[i] is not None and preferred[i] in [action[0] for action in by_index[event["index"]]["actions"]]
                  for i, event in enumerate(selected) if event["index"] in by_index)
    eligible = sum(lane is not None for lane in preferred)
    patterns=pattern_rules.audit(timeline,_source(decoded)[1],plan)
    if not patterns['pass']:raise ValueError('Serialized pattern policy failed: '+str(patterns['errors'][:8]))
    metrics = {"pattern_rules":patterns,"generator": VERSION, "seed": int(seed), "columns": cols, "level": int(level), "tier": tier,
               "requested_notes": int(target_notes), "effective_note_target": effective_target,
               "source_notes": sum(len(e["lanes"]) for e in source_events), "source_onsets": len(source_events),
               "selected_onsets": len(selected), "omitted_onsets": len(selected) - len(plan),
               "omission_ratio": omission_ratio,
               "motif_blocks_considered": motif_count, "source_repairs": source_repairs,
               "motif_lane_preferences": eligible, "motif_lane_matches": matched,
               "motif_lane_match_ratio": matched / max(1, eligible),
               "repairs": repairs, "limits": limits, "footsteps": plan, "verification": verification,
               "rhythm": rhythm_audit(source_events, _source(decoded)[1]),
               "spatial": spatial_audit(_source(decoded)[1], cols),
               "sha256": hashlib.sha256(encoded).hexdigest()}
    return decoded, metrics
