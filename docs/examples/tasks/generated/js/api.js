"use strict";
// GENERATED native JS types + codec — do not edit. Pairs with cbor.js.
const { CInt, CFloat, CText, CBytes, CBool, CArr, CMap, CNull, cget, cgetOrNull, mapFromCbor, cmapEntries, compareCodePoints, isNull, expectInt, expectFloat, expectText, expectBytes, expectBool, expectArray, expectMap, enumFromWire, enumFromCbor, decode } = require("./cbor.js");

const TaskState = Object.freeze({ open: 0, doing: 1, done: 2 });
const TaskStateValues = new Set([0, 1, 2]);
function TaskStateFromWire(v) { return enumFromWire(v, "TaskState", TaskStateValues); }
function TaskStateFromCbor(c) { return enumFromCbor(c, "TaskState", TaskStateValues); }

class User {
  static get MAX_DEPTH() { return 32; }
  static get MAX_ENCODED_LEN() { return null; }
  constructor(o = {}) {
    this.id = o.id;
    this.name = o.name;
  }
  toCbor() {
    const m = [
      [1, CInt(this.id)],
      [2, CText(this.name)],
    ];
    return CMap(m);
  }
  static fromCbor(c) {
    const v = new User();
    v.id = expectInt(cget(c, 1));
    v.name = expectText(cget(c, 2));
    return v;
  }
  static decode(bytes) {
    return User.fromCbor(decode(bytes, { maxDepth: User.MAX_DEPTH, maxEncodedLen: User.MAX_ENCODED_LEN }));
  }
}

class Comment {
  static get MAX_DEPTH() { return 32; }
  static get MAX_ENCODED_LEN() { return null; }
  constructor(o = {}) {
    this.author = o.author;
    this.text = o.text;
  }
  toCbor() {
    const m = [
      [1, this.author.toCbor()],
      [2, CText(this.text)],
    ];
    return CMap(m);
  }
  static fromCbor(c) {
    const v = new Comment();
    v.author = User.fromCbor(cget(c, 1));
    v.text = expectText(cget(c, 2));
    return v;
  }
  static decode(bytes) {
    return Comment.fromCbor(decode(bytes, { maxDepth: Comment.MAX_DEPTH, maxEncodedLen: Comment.MAX_ENCODED_LEN }));
  }
}

class Task {
  static get MAX_DEPTH() { return 32; }
  static get MAX_ENCODED_LEN() { return null; }
  constructor(o = {}) {
    this.id = o.id;
    this.title = o.title;
    this.state = o.state;
    this.assignee = o.assignee;
    this.comments = o.comments;
    this.labels = o.labels;
  }
  toCbor() {
    const m = [
      [1, CInt(this.id)],
      [2, CText(this.title)],
      [3, CInt(this.state)],
      [4, (this.assignee != null ? this.assignee.toCbor() : CNull())],
      [5, CArr(this.comments.map((e) => e.toCbor()))],
      [7, CArr([...this.labels.entries()].sort((a, b) => compareCodePoints(a[0], b[0])).map(([k, v]) => CMap([[1, CText(k)], [2, CText(v)]])))],
    ];
    return CMap(m);
  }
  static fromCbor(c) {
    const v = new Task();
    v.id = expectInt(cget(c, 1));
    v.title = expectText(cget(c, 2));
    v.state = TaskStateFromCbor(cget(c, 3));
    { const f = cget(c, 4); v.assignee = isNull(f) ? null : User.fromCbor(f); }
    v.comments = expectArray(cget(c, 5)).map((e) => Comment.fromCbor(e));
    v.labels = mapFromCbor(new Map(), cget(c, 7), (key) => expectText(key), (value) => expectText(value));
    return v;
  }
  static decode(bytes) {
    return Task.fromCbor(decode(bytes, { maxDepth: Task.MAX_DEPTH, maxEncodedLen: Task.MAX_ENCODED_LEN }));
  }
}

class Event {
  static get MAX_DEPTH() { return 32; }
  static get MAX_ENCODED_LEN() { return null; }
  constructor(o = {}) {
    this.ts = o.ts;
    this.text = o.text;
  }
  toCbor() {
    const m = [
      [1, CInt(this.ts)],
      [2, CText(this.text)],
    ];
    return CMap(m);
  }
  static fromCbor(c) {
    const v = new Event();
    v.ts = expectInt(cget(c, 1));
    v.text = expectText(cget(c, 2));
    return v;
  }
  static decode(bytes) {
    return Event.fromCbor(decode(bytes, { maxDepth: Event.MAX_DEPTH, maxEncodedLen: Event.MAX_ENCODED_LEN }));
  }
}

module.exports = { TaskState, TaskStateFromWire, TaskStateFromCbor, User, Comment, Task, Event };
