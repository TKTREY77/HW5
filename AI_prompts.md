# AI Prompts Log — Homework 5: Campus Customs Multi-Agent Operations

Every prompt given to the AI assistant (initial + follow-ups), organized by problem number and title. Prompts are logged verbatim and stay under a problem until work on the next problem begins.

**Edit policy:** If a prompt is revised after the fact (e.g., to fix a mistake or revisit a problem), the original text stays in place and an **✏️ Edit note** is added directly beneath it describing what was changed manually and why.

---

## Setup

### Prompt 1

> Today we're working on Homework 5: Campus Customs Multi-Agent Operations, and all of our work needs to be done inside the connected folder called "HW5".
>
> To start, please unzip `data.zip` and make a copy of `data/campus_customs.db` called `data/campus_customs_new.db`. We will point our MCP server and backend at this new copy so we can keep the original database clean and reset it whenever needed.
>
> For our workflow, we'll go through the assignment problem by problem. I need you to create a file named `AI_prompts.md` where we will log every single prompt (initial ones and any follow-ups) organized by problem number and title, right up until we move on to the next problem.
>
> As a quick overview, we'll be building three connected pieces: an MCP server, a FastAPI backend for a 5-agent team (Boss, Inventory, Accounting, Facilities, and Customer Service), and a React dashboard so a human can monitor the agents and approve requests.
>
> Before we jump in, keep these key rules in mind:
>
> * Use `desk.date_today` as "today" and pull vendor lead times from the `vendors` table.
> * Vendors won't ship if they have open unpaid invoices.
> * Human approval is strictly required for any payments, the pay tool must refuse if cash is insufficient (no negative balances), and money only goes out (no incoming revenue).
> * Never email real customers or call real vendors—drafts stay on the board.
> * Most importantly, every agent must use only `gpt-6-luna` through Portkey using `PORTKEY_API_KEY`. This is in an .env file that I used earlier in AI Foundations (Fall 1 - 2026) folder. See if you can find it and if not I'll find it for you (but pls try first)

---

## Problem 1: Vibe Coder Prompts

### Prompt 2

> You've already basically done this, but for tracking's sake: For Problem1: Vibe Coder Prompts, every one of my prompts being saved to AI_prompts.md (including the last one) with the problem number and title, all prompts used for that problem (initial and follow-ups) until I begin the following problem. I might make mistakes and need to go back, so allow me to edit this, but note the edit (i.e. under the prompt you can say the adjustment that I made manually in order to ensure transparency).

### Prompt 3

> well no, so that first prompt I sent should just be "Setup" this second prompt (prompt 2) should be "Problem 1: Vibe Coder Prompts". This prompt I'm writing now should be prompt 3 and nested under Problem 1 prompts

---

## Problem 2: Studying the Campus Customs Database

### Prompt 4

> Problem 2: Studying the campus customs database. Open data/campus_customs.db and look through it. Not its tables and fields. You've basically already done this in the setup, but copy the original file to data/campus_customs_new.db (I know you've already done this via setup). We'll be updating this later with future prompts.
>
> Within this, study the 3 open tickets so you see how they link to other tables. Then create output/harness.md. For each table, list the fields and a line regarding how the table is important for the agents. Similar to above, we will continue to add to this file as we work.

### Prompt 5

> Okay, interesting. So we're tight on cash... Let's see how this plays out as we go

---

## Problem 3: Build the MCP server

### Prompt 6

> Now we are moving on to Problem 3: Build the MCP server. Please build an MCP server in the mcp_server/ directory using FastMCP that talks to data/campus_customs_new.db (you do not need to connect or run it yet). Write three clear tools that you know will be needed for tickets 101, 102, and 103 in the database, making sure to only use real database information without inventing any data. Next, update output/harness.md by listing each of your three MCP tools, detailing which database table each reads, which ticket (101, 102, or 103) it helps unlock, and writing a concise one-sentence explanation tying the tool directly to why it is right for that specific ticket (avoiding vague descriptions like "reads inventory"). Finally, add a short mcp_server/README.md explaining what the MCP server is for, which database file it uses, and summarizing its three tools, and remember to log this exact prompt under "## Problem 3: Build the MCP server" in AI_prompts.md!

---

## Problem 4: Add the MCP server to vibe coder and test each tool

### Prompt 7

> Now we are moving on to Problem 4: Add the MCP server to vibe coder and test each tool. First, add our MCP server configuration to this project so that Claude Code can call the tools, saving the connection JSON in .mcp.json at the project root. Next, test each of your three MCP tools using Claude Code and save the execution evidence into output/mcp_smoke.json. For every tool tested in that file, make sure to include the exact prompt you asked, the tool name, and the tool output (ensuring the output matches the actual values in data/campus_customs_new.db). Finally, remember to log this exact prompt under "## Problem 4: Add the MCP server to vibe coder and test each tool" in AI_prompts.md before moving forward!

### Prompt 8

> Let's go with option A. I also don't understand how the CLaude CLI is a problem. Can I help with this as well?

### Prompt 9

> *(Screenshot only, no text: terminal running `claude` in HW5, showing Claude Code v2.1.280's first-run "Choose the text style" theme picker.)*

### Prompt 10

> *(Screenshot only, no text: Claude Code prompt "New MCP server found in this project: campus-customs" with options Use this MCP server / Use this and all future MCP servers in this project / Continue without using this MCP server.)*

### Prompt 11

> Okay, we should be good to go in terminal now. thanks
>
> *(Screenshot: Claude Code v2.1.280 logged in (Opus 5, Claude Enterprise) in ~/…/HW5.)*

### Prompt 12

> no, this looks good. Don't rerun now, only if the tools change and when relevant.

---

## Problem 5: Build the agent team and grow the MCP tools

### Prompt 13

> Now we are moving on to Problem 5: Build the agent team and grow the MCP tools. Please build the agentic team for Campus Customs using PydanticAI with five distinct roles: Boss, Inventory, Accounting, Facilities, and Customer Service, ensuring they have full connectivity to delegate work to one another. Store individual agent prompts in backend/prompts/ (one file per agent), put data types in backend/models.py, and place the main agent logic under backend/. Write detailed, agent-specific prompts covering all relevant shop rules, and make sure every agent strictly uses gpt-6-luna via PORTKEY_API_KEY. Additionally, expand our MCP server with any extra tools the agents need to resolve the open tickets in data/campus_customs_new.db without creating any secondary tools that bypass MCP. Wire all agents to append each execution step to output/audit_trail.json continuously without wiping the file between runs. Finally, update output/harness.md to list every agent and MCP tool along with its corresponding database table, add a safety section in output/harness.md covering guardrails for real money/customers and token limits, update mcp_server/README.md to match the expanded tool list, and remember to log this exact prompt under "## Problem 5: Build the agent team and grow the MCP tools" in AI_prompts.md before moving forward!

### Prompt 14

> yeah, add the new tools

---

## Problem 6: Plan the three tickets

### Prompt 15

> Now we are moving on to Problem 6: Plan the three tickets. Build an HTML dashboard in output/desk_tickets.html that can be opened by double-clicking, containing separate tabs for tickets 101, 102, and 103, as well as placeholder tabs for Cash and Reflection (which can be left blank or marked with a "coming later" note for now). Under each ticket tab, create an Expected section (leaving room for an Actual section to be filled in later after the agent runs) and outline in your own words who the Boss should call first and why, all expected agent-to-agent delegations rather than blanket-calling every agent, and which specific MCP tools you expect to be used during that run. Avoid generic plans that send every specialist on every ticket, as these will score low.

---

## Problem 7: Backend routes

### Prompt 16

> Now we are moving on to Problem 7: Backend routes. In backend/main.py, use FastAPI to build the backend routes required by our React frontend dashboard: returning all three tickets and their open/resolved status, accepting a ticket ID to run the agent team, returning recent agent events (agent statements and tool usage) for dashboard auto-refreshes, approving a payment or purchase upon human click (where agents only prepare payments and this endpoint actually executes the cash change), fetching current checking balances from cash_accounts, and resetting the database to original values for fresh runs. Ensure the backend can be started from backend/ using uvicorn main:app --reload --port 8000 at http://localhost:8000. Additionally, update output/harness.md to list each created route on a single line with its URL path and brief functionality description

### Prompt 17

> Yes, smoke test those new tools just in case

### Prompt 18

> will the missing permission on list_tickets pose an issue?

### Prompt 19

> whoops, delete that prompt. My bad. I left and forgot we already ran that

> ✏️ **Edit note:** At the user's request, the previous Prompt 19 was deleted. It was an accidental re-paste of the Problem 7 prompt (identical to Prompt 16, prefixed with "Okay"), and no work was done from it. This message took its number.

---

## Problem 8: Agent dashboard

### Prompt 20

> Okayso
>
> Problem 8: Agent dashboard. Please build the frontend dashboard in frontend/ using React, Vite, and TypeScript, connecting it to our backend at http://localhost:8000 (and configuring backend CORS to allow the Vite origin, typically http://localhost:5173). Ensure the board lists all three tickets, lets users select a ticket to run the agent team, displays live activity showing what each agent is saying/doing, marks tickets as resolved upon completion, provides a short summary of each agent's actions, supports human approval for payments/purchases, and displays the current checking balance (updating dynamically after payments). Design a clean, thoughtful, and creative layout that feels like a real desk workspace users would enjoy using. The frontend should launch using npm run dev from frontend/. Finally, write output/design.md detailing your design and UI/UX choices where you explain the layout, visual distinction between agents, representation of cash and resolved tickets, and the creative elements that elevate the user experience

---

## Problem 9: Resolve the tickets

### Prompt 21

> on to Problem 9: Resolve the tickets. Before running the agents on the three tickets, reset data/campus_customs_new.db so you start clean, taking note of the starting checking balance. Run all three tickets (101, 102, 103) on the board until each is fully resolved, ensuring real runs append continuously to output/audit_trail.json. Next, update output/desk_tickets.html by filling in the Actual section on each ticket tab (detailing which agents worked, what they delegated, and which tools were used alongside the original Expected section) and completing the Cash tab with an itemized breakdown: the starting checking balance, exact cash changes per resolved ticket (with payment/purchase details and dollar amounts), and the ending balance matching cash_accounts in the working database. In addition, save output/resolved_tickets.json (containing ticket ID, final status, short outcome, individual agent contributions, and human approvals) and build output/resolved_board.html with screenshots of your React board for each resolved ticket. Finally, finish updating output/harness.md so that it completely covers database tables, MCP tools, the five agents, API routes, the dashboard layout, and safety rules.

### Prompt 22

> *(Answers to Claude's approval question during the run.)* Slips: **"Sign all three (Recommended)"**. #1 pay invoice #501 $840 to Bulldog, #2 pay rent $2,400 to Elm City Properties, #3 approve the 10% hoodie discount quote. Signer name: **"Teddy"**.

### Prompt 23

> Can you launch in the browser again so I can check and then we can get to problem 10?

### Prompt 24

> wait so where is the window with the reflection and cash tab

---

## Problem 10: Reflection

### Prompt 25

> Okay, gotcha thanks. So for the reflection tab, here's what we're going to do:
>
> Now we are moving on to Problem 10: Reflection. For `output/desk_tickets.html`  (Reflection tab) I am going to answer the following questions (Please load these into the reflection tab):
>
> 1. Agent Performance: How would you evaluate the performance of the agents on each ticket and why?
>    1. My response: Well in that it assessed the quantitative elements well, understood the constraints, and prioritized effectively. Also, (directionally) instructing the user how to resolve and the order of operations is a good idea, albeit a bit micro-manage-y. Well in that it followed instructions and didn't send messages or pay bills without my sign-off. Poorly in that they kind of went around in circles on ticket 101 (kept circling and confirming size S was 0), on 102 (kept confirming the rent when it was already established and cycled too much) and the same on 103, but alas, worth checking. The react page is also a little chunky tbh and the UI isn't ideal (a lot of embedded scrolling)
> 2. Actual vs. Expected: For each ticket, how did the actual agent execution compare to the expected plans we wrote in Problem 6?
>    1. Mr Response: Directionally well. It followed the rules and achieved the desired output, just wasn't that token-efficient in doing so. The final cash tab looks clear. The audit trail and resolved board provides a good resource to double check and confirm it did what it said it would do.
> 3. Single Agent vs. Multi-Agent Team: What task(s) would have been simpler to handle as a single agent with tools instead of a multi-agent team, and why?
>    1. My Response: Well honestly I think having this many agents wasn't helpful in this case. Maybe for a real store or business, but clearly there was too much hand off and cycling that wasn't very token-efficient. For this task, simply assessing dependencies for each task (i.e. timeframes to pay and cash limitations) could be done by one agent and passed to the boss, who could form their response for next steps. Maybe multi-agent would still have been good, but I feel like I had too many agents. I should have specified this from the beginning and put tokenomics in the harness.
> 4. Solvable New Problems: Describe three new operational problems Campus Customs might face that this agent team could successfully solve using the MCP tools we built.
>    1. My Response: I think clearly cash management. Also, phasing of future orders could be helpful. So first, phasing: The agent could be helpful for, say, managing 50 new orders of different timeframes and it's too much for a person to handle. Can project the cash needs and expected timeframes for each in a way that a human can't. Secondarily, I would say probably staffing management, primarily around peoples' complex schedules and their associated pay rates and needs. Anything that's multi-variable with fixed knowns and overlapping dependencies can likely be done more easily by AI. Finally, (as we learned before) pitching new business to Yale organizations AND doing inventory planning for those orders (provided the human user reviews and signs off on those orders... see below).
> 5. Unsolvable New Problems: Describe three new operational problems Campus Customs might face that this agent team could not solve with the current tools, explaining the additional tools and agent roles required to solve them.
>    1. My Response: First, full inventory management not so much. You need real people as things get lost and misplaced. A human would need to update this system, otherwise it might say something is in stock when it's not. I ran into this issue frequently in production planning (with tofu) as the total you have never really matches as things get misplaced or go back (food relevant). Second, I would say things with flexible timeframes... technically rent is due in 2 days... but is it? if you need to flex cash you can pay late. Will the landlord really kick you out after one late payment. What's the qualitative arrangement you have. these are things it can't know for which human intuition is required. Finally, full automation for order management. You might have heard about the man who went to the AI-powered Taco Bell drive through and ordered 10,000 water cups. A human would know this is a joke, but the AI would have trouble judging if an order is high conviction. Say someone comes in and says they want to order 100 sweaters for a club event, but the human knows the club has poor funding or it would be unrealistic for them to afford this... This is where inventory planning would break down (I know I contradict myself from above slightly).
>
> Have I missed something relevant? (i.e. that every answer ties specifically back to this app, our database, and the three tickets (101, 102, 103) we ran

### Prompt 26

> okay, add that the Boss caught that the $264 restock was $104. I suppose that's a good call for 1. 20 tool calls and 4.7 minutes is too much, so add that and emphasize in the "going in circles"
>
> Oh, for 2 do the same. Agreed on number 1 in that it worked to plan, but again, too much cycling and burning tokens. Calling the boss was not good for 102... For 103, I would say that goes to plan... 10% is within range. Help me assign the rough token usage per ticket if possible and if not add this 130k total ticket number.
>
> For 3, Agreed on this as examples here.
>
> For 4, shift staffing to 5. I guess you're right. I was trying to get at the multi-variate and dependency thing but I guess out of the box, staffing is unsolvable. We offered in-stock alternatives before, so let's go with the Bill and rent calendar to project future bills and expected payments. Potentially even integrating with Quickbooks or another accounting software.
>
> For 5, on inventory accuracy, I hear you, but you do need human verification for full inventory management. That was my point. I guess you could add payment terms etc, but again it's more the social understanding so I stand by this one. I've experienced it. Knowing the social consequences is something an AI would struggle with. As for the taco bell example, you could use AI like this and then have a "gut-check" agent or human, but again, I think then adding a human back somewhat defeats this point... This is a backend system in its essence.
>
> Update my responses accordingly with the note that you've helped me reform my responses.

### Prompt 27

> yeah, drop staffing

### Prompt 28

> Also, from "...the relection tab, here's what we're going to do:" go back and make that all problem 10 in the AI_prompt file

---

## Problem 11: Submit to GitHub

### Prompt 29

> Finally, Problem 11: Submit to GitHub:  Please prepare the repository for public submission so graders can easily clone and run it. Ensure that both database files (data/campus_customs.db and data/campus_customs_new.db) are included in data/, but make sure our real .env file is gitignored and NOT pushed to GitHub (including an .env.example file instead). Ensure that our project structure matches the expected file layout with AI_prompts.md, requirements.txt, .env.example, .gitignore, .mcp.json, README.md, data/, mcp_server/, frontend/, backend/, and output/ (including harness.md, mcp_smoke.json, desk_tickets.html, design.md, resolved_tickets.json, resolved_board.html, audit_trail.json, and github_url.txt). Make sure README.md clearly explains how to copy the original DB to the working copy for a clean run, start the MCP server, launch the FastAPI backend, start the React board, and reset the DB before a full run. Once pushed, please save the public GitHub repo URL into output/github_url.txt. What other information do you need from me?

### Prompt 30

> When you're done, open the link in github so I can submit the assignment
