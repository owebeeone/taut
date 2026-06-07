"use strict";
// GENERATED native JS types + codec — do not edit. Pairs with cbor.js.
const { CInt, CText, CBytes, CBool, CArr, CMap, CNull, cget, cmapEntries, isNull } = require("./cbor.js");

const TaskState = Object.freeze({ open: 0, doing: 1, done: 2 });

class User {
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
    v.id = cget(c, 1).i;
    v.name = cget(c, 2).s;
    return v;
  }
}

class Comment {
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
    v.text = cget(c, 2).s;
    return v;
  }
}

class Task {
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
      [7, CArr([...this.labels.entries()].sort((a, b) => a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0).map(([k, v]) => CMap([[1, CText(k)], [2, CText(v)]])))],
    ];
    return CMap(m);
  }
  static fromCbor(c) {
    const v = new Task();
    v.id = cget(c, 1).i;
    v.title = cget(c, 2).s;
    v.state = cget(c, 3).i;
    { const f = cget(c, 4); v.assignee = isNull(f) ? null : User.fromCbor(f); }
    v.comments = cget(c, 5).arr.map((e) => Comment.fromCbor(e));
    v.labels = new Map(cget(c, 7).arr.map((e) => [cget(e, 1).s, cget(e, 2).s]));
    return v;
  }
}

class Event {
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
    v.ts = cget(c, 1).i;
    v.text = cget(c, 2).s;
    return v;
  }
}

module.exports = { TaskState, User, Comment, Task, Event };
