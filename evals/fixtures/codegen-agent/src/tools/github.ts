import { Octokit } from "@octokit/rest";
import { tool } from "@anthropic-ai/claude-agent-sdk";
import { z } from "zod";
import { withApproval, ApprovalDenied, type GatedAction } from "../approvals.js";
import { record } from "../audit.js";
import type { RunBudget } from "../budget.js";
import type { RunContext } from "../identity.js";

const DISPATCHABLE_WORKFLOWS = new Set(["ci.yml", "integration.yml"]);
const APPROVAL_WAIT_MS = 30 * 60_000;

export function githubTools(ctx: RunContext, budget: RunBudget, token: () => string) {
  const gh = () => new Octokit({ auth: token() });
  const { owner, name: repo } = ctx.repo;

  async function headSha(branch: string): Promise<string> {
    const { data } = await gh().repos.getBranch({ owner, repo, branch });
    return data.commit.sha;
  }

  const createPullRequest = tool(
    "create_pull_request",
    "Open a pull request from an agent/* branch. A maintainer must approve it in the approvals console first.",
    {
      head: z.string().regex(/^agent\/[A-Za-z0-9._\/-]{1,100}$/),
      base: z.string().min(1).max(100),
      title: z.string().min(1).max(200),
      body: z.string().max(20_000),
    },
    async ({ head, base, title, body }) => {
      const sha = await headSha(head);
      const { data: cmp } = await gh().repos.compareCommits({ owner, repo, base, head: sha });
      const action: GatedAction = {
        operation: "create_pull_request",
        target: `${owner}/${repo}`,
        args: { head, base, title, body, headSha: sha, issue: ctx.issueNumber },
        summary: [
          `PR ${head} -> ${base}: ${title}`,
          `${cmp.files?.length ?? 0} files, +${cmp.files?.reduce((n, f) => n + f.additions, 0) ?? 0} / -${cmp.files?.reduce((n, f) => n + f.deletions, 0) ?? 0}`,
          ...(cmp.files ?? []).slice(0, 50).map((f) => `  ${f.status} ${f.filename}`),
        ].join("\n"),
      };
      try {
        const pr = await withApproval(
          ctx,
          action,
          Math.min(APPROVAL_WAIT_MS, budget.remainingMs()),
          async () => {
            if ((await headSha(head)) !== sha) throw new ApprovalDenied(`${head} moved after approval`);
          },
          async (approvalId) => {
            const { data } = await gh().pulls.create({ owner, repo, head, base, title, body });
            await record(ctx, { kind: "tool_result", tool: "create_pull_request", approvalId, outcome: "ok", detail: data.html_url });
            return data;
          },
        );
        return { content: [{ type: "text", text: `opened ${pr.html_url}` }] };
      } catch (err) {
        if (err instanceof ApprovalDenied) return { content: [{ type: "text", text: err.message }], isError: true };
        throw err;
      }
    },
  );

  const triggerWorkflow = tool(
    "trigger_workflow",
    "Dispatch ci.yml or integration.yml on an agent/* branch. Requires maintainer approval.",
    {
      workflow: z.string(),
      ref: z.string().regex(/^agent\/[A-Za-z0-9._\/-]{1,100}$/),
    },
    async ({ workflow, ref }) => {
      if (!DISPATCHABLE_WORKFLOWS.has(workflow)) {
        return { content: [{ type: "text", text: `${workflow} cannot be dispatched` }], isError: true };
      }
      const sha = await headSha(ref);
      const action: GatedAction = {
        operation: "trigger_workflow",
        target: `${owner}/${repo}/${workflow}`,
        args: { workflow, ref, headSha: sha },
        summary: `dispatch ${workflow} on ${ref} @ ${sha.slice(0, 12)}`,
      };
      try {
        await withApproval(
          ctx,
          action,
          Math.min(APPROVAL_WAIT_MS, budget.remainingMs()),
          async () => {
            if ((await headSha(ref)) !== sha) throw new ApprovalDenied(`${ref} moved after approval`);
          },
          async (approvalId) => {
            await gh().actions.createWorkflowDispatch({ owner, repo, workflow_id: workflow, ref });
            await record(ctx, { kind: "tool_result", tool: "trigger_workflow", approvalId, outcome: "ok" });
          },
        );
        return { content: [{ type: "text", text: `dispatched ${workflow} on ${ref}` }] };
      } catch (err) {
        if (err instanceof ApprovalDenied) return { content: [{ type: "text", text: err.message }], isError: true };
        throw err;
      }
    },
  );

  return [createPullRequest, triggerWorkflow];
}
