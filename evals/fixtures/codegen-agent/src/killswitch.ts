import { Octokit } from "@octokit/rest";
import { config } from "./config.js";
import type { RunContext } from "./identity.js";

export class RunHalted extends Error {}

export async function isHalted(ctx: RunContext, token: string): Promise<boolean> {
  const gh = new Octokit({ auth: token });
  const { data } = await gh.issues.listLabelsOnIssue({
    owner: ctx.repo.owner,
    repo: ctx.repo.name,
    issue_number: ctx.issueNumber,
  });
  return data.some((label) => label.name === config.haltLabel);
}
