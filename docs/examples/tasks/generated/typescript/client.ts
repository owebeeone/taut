// GENERATED typed client over the generic tautClient (call/subscribe).
import type { tautClient } from "../../../../trial/ts/src/client.ts";
import type * as api from "./api.ts";

export class TasksClient {
  private c: tautClient;
  constructor(c: tautClient) { this.c = c; }
  create(title: string): Promise<api.Task> {
    return this.c.call("create", { title }) as Promise<api.Task>;
  }
  comment(task_id: number, author: User, text: string): Promise<api.Comment> {
    return this.c.call("comment", { task_id, author, text }) as Promise<api.Comment>;
  }
  set_state(id: number, state: TaskState): Promise<api.boolean> {
    return this.c.call("set_state", { id, state }) as Promise<api.boolean>;
  }
  tasks_subscribe(onEvent: (event: string, value: unknown) => void): () => void {  // atom
    return this.c.subscribe("tasks.subscribe", {}, onEvent);
  }
  activity_subscribe(onEvent: (event: string, value: unknown) => void): () => void {  // log
    return this.c.subscribe("activity.subscribe", {}, onEvent);
  }
}
