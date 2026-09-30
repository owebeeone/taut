// GENERATED native TypeScript types — do not edit.

export type TaskState = "open" | "doing" | "done";

export interface User {
  id: bigint;
  name: string;
}

export interface Comment {
  author: User;
  text: string;
}

export interface Task {
  id: bigint;
  title: string;
  state: TaskState;
  assignee: User | null;
  comments: Comment[];
  labels: Map<string, string>;
}

export interface Event {
  ts: bigint;
  text: string;
}

