# User guide

Source for the report appendix "User guide". Stream C wrote the sign-in, knowledge graph, message draft, assistant, rules, users and audit sections. Streams A and B fill in the placeholder pages.

This guide assumes AnchorAI is installed and seeded (see the installation guide).

## 1. Getting started

### Who uses AnchorAI

AnchorAI has three roles. The role decides which pages appear in the sidebar. The server checks the role again on every request, so a page that is hidden cannot be reached by typing its address.

| Role | Who | Lands on | Can use |
|---|---|---|---|
| Staff | Front desk, trainers | My contacts | My contacts, Member 360 (read only), Assistant, message drafts |
| Manager | Club manager | Dashboard | Everything Staff can, plus Dashboard, Segments, Members, Weekly plan, Scenarios, Knowledge graph, Events & roster |
| Admin | Operator, owner | Dashboard | Everything, plus Rules, Offers & constraints, Data & models, Users, Audit log, Settings |

### Sign in

1. Open the web app (<http://localhost:5173> in development).
2. Enter your username and password, then select **Sign in**.
3. The seeded demo users are `admin`, `manager`, `staff1` and `staff2`. The password for all of them is `anchorai`. The sign-in page lists them under "Demo accounts".

<!-- screenshot: sign-in page with the demo accounts box -->

If the username or password is wrong, the page says "Invalid username or password". If it says "Could not reach the server", the API is not running.

A session lasts 12 hours. After that, or if an admin deactivates your account or resets your password, the next page you open sends you back to the sign-in page. After you sign in again you return to the page you were on.

### Sign out

Open the account menu at the top right (your initials, name and role) and select **Log out**.

### The sidebar

The sidebar groups pages for your role:

| Group | Pages |
|---|---|
| Insights | Dashboard, Segments, Members |
| Planning | Weekly plan, Scenarios, Knowledge graph, Events & roster |
| Front desk | My contacts, Assistant |
| Administration | Rules, Offers & constraints, Data & models, Users, Audit log, Settings |

Use **Collapse** at the bottom to shrink the sidebar to icons. On a narrow screen the sidebar is hidden behind the menu button at the top left. The search box at the top finds a member by ID and opens their Member 360 page.

### Theme

Select the sun or moon button at the top right and pick **Light**, **Dark** or **System**. System follows your device setting. The sign-in page has the same button. The choice is remembered in your browser.

<!-- screenshot: top bar with the theme menu open -->

### The assistant button

On every page except the Assistant page, a round button at the bottom right opens the assistant in a side panel. See section 6.

## 2. Pages written by Stream A and Stream B

These pages are in the application. Their sections are to be written by the owning stream.

### Dashboard (W10)

To be written by Stream A.

### Segments (W11)

To be written by Stream A.

### Members (W12)

To be written by Stream A.

### Member 360 (W13)

To be written by Stream A, except the two panels below, which Stream C owns. Open a member from the Members list, the global search, or any member link in this app.

**Rule trace panel.** It shows what the rule base concludes for this member.

- *Allowed offers* are the offers the playbook proposes and no guardrail blocks, each with its channel. The small code on the right is the rule ID. Hover over it for the rule's description.
- *Blocked* lists offers a guardrail removed, with the reason. "All offers" means a guardrail blocks every offer.
- *Rules fired, in order* lists each rule that matched, from first to last. Each step says what the rule concludes, proposes or blocks, and shows the facts that made it match (for example "Trend ratio: 0.62"). The step colour tells the kind: violet for a derived fact, green for a playbook proposal, red for a guardrail.
- **Draft message** next to an allowed offer opens the message draft dialog (section 5).

<!-- screenshot: Member 360 rule trace panel -->

**Knowledge-graph neighbourhood panel.** It draws the member's club, classes, instructors and events as a graph. See "Member neighbourhood" in section 3. If Neo4j is down, the panel shows "Knowledge graph unavailable" and the rest of the page works.

### Weekly plan: plan builder and review (W14, W15)

To be written by Stream B.

### Scenarios (W17)

To be written by Stream B.

### My contacts (W20, W21)

To be written by Stream B.

### Offers & constraints (W41)

To be written by Stream A.

### Data & models (W42)

To be written by Stream A.

### Settings (W45)

To be written by Stream B.

## 3. Knowledge graph explorer (W18)

**Who:** managers and admins. **Where:** sidebar, Planning, **Knowledge graph**.

The page has two parts: **Simulate an event** and **Member neighbourhood**. A **Manage events & roster** link leads to the Events and roster page (section 4).

### Simulate an event

Use this to see who an instructor leaving or a class closing would affect. A simulation changes nothing in the data.

1. In **Event**, open the list. Instructors are under "Instructor leaves" and classes under "Class cancelled". Type in the list to filter it. An entry marked "(already happened)" has a recorded event.
2. Select **Run simulation**.
3. Read the banner "If …" and the three tiles:
   - **Members affected**: members linked to that instructor or class.
   - **High risk**: how many of them are in the high-risk band.
   - **Newly trigger rules**: members who match at least one rule they would not match today.
4. Read the table. For each member it shows the risk band and score, the share of their visits that were with the instructor (instructor events only), the rules they would newly trigger, and the offers the rules would then allow. Use the table's search, sort and CSV export as on other tables.
5. Select a member ID to draw their neighbourhood on the right.

<!-- screenshot: simulate an event result with the three tiles and the affected members table -->

If the banner says the knowledge graph is out of date, a roster edit has been saved but the graph has not been rebuilt, so counts may miss it. Reload the graph from the Events & roster page.

### Member neighbourhood

1. Type a member ID such as `M0155` and select **Show**, or pick a member from the simulation table.
2. Read the graph. Each node has its name inside it, so colour is not the only cue.

| Node | Colour |
|---|---|
| Member | blue |
| Club | grey |
| Class | teal |
| Instructor | purple |
| Event | red |
| Offer | amber |

   A member with a thick red border is in the high-risk band. The legend under the graph repeats this. Links are labelled with their type.
3. Select **Open … in Member 360** under the graph to go to the member's page.

<!-- screenshot: neighbourhood graph with a high-risk member -->

## 4. Events and roster

**Who:** managers and admins. **Where:** sidebar, Planning, **Events & roster**, or **Manage events & roster** on the Knowledge graph page.

This page is where the club records what has really happened. The graph is rebuilt after each change, and rules that read graph signals (a lost instructor, a cancelled class) then fire for the affected members. Churn scores do not change when an event is recorded. Added classes have no attendance until the data is rebuilt.

It has two tabs, **Instructors** and **Classes**. Each table can be searched and exported.

To add an instructor:

1. On the **Instructors** tab, select **Add instructor**.
2. Enter a name, pick a club, and select **Add**.

To add a class:

1. On the **Classes** tab, select **Add class**.
2. Enter a name, pick a club, then pick the instructor. Only instructors still at that club are listed. Select **Add**.

To change who teaches a class: on the **Classes** tab, select **Change instructor** on its row, pick the new instructor and confirm.

To record that an instructor has left: on the **Instructors** tab, select **Mark as left** on their row, set the week and an optional note, and select **Mark as left**. Their classes then lose the instructor in the graph.

To record that a class is cancelled: on the **Classes** tab, select **Cancel class** on its row, set the week and an optional note, and confirm.

To undo an event: select **Reinstate** on the instructor or class row and confirm. Status goes back to Active.

The **Source** column shows whether a row was generated with the data ("Generated") or added here ("Added here").

The line at the top of the page shows when the graph was last reloaded. Select **Reload knowledge graph** to rebuild it by hand.

<!-- screenshot: Events & roster page, Classes tab -->

### When Neo4j is unavailable

- The roster edits above are still saved. A warning toast says "the knowledge graph is not updated", and the page shows "Edits are saved, but the knowledge graph has not been rebuilt from them". Start Neo4j, then select **Reload knowledge graph**.
- Simulations and neighbourhood graphs show "Knowledge graph unavailable".
- The rest of the app works. Rules that read graph signals do not fire for new events until the graph is reloaded.

## 5. Message drafts (W22)

**Who:** every role. **Where:** the **Draft message** button next to an allowed offer in a rule trace (Member 360).

A draft is a short message to the member about the offer. AnchorAI never sends it. You copy it into your own messaging tool.

1. On a Member 360 page, find the offer under *Allowed offers* in the rule trace and select **Draft message**.
2. Pick a channel at the top: SMS, email, call or in person. Only channels the offer supports are listed. If you pick a channel other than the one the playbook proposes, a notice says so.
3. Wait for the draft. The tag above the text says **AI draft** (written by the language model) or **Template** (written from a fixed pattern).
4. Edit the text. For email, edit the subject too. For SMS the character count is shown.
5. Select **Copy**. The button reads "Copied" for a moment.
6. Open **Facts used** to see the evidence lines the draft was written from.

Select **Regenerate** for a new draft. If you have edited the text, AnchorAI asks before discarding your edits. Switching channel does the same.

<!-- screenshot: message draft dialog with the AI draft tag -->

What to expect:

- A draft never mentions churn, risk, scores or models, and never states a number that is not in the evidence. If the language model's text breaks these checks, AnchorAI uses the template instead.
- If the language model is offline, you get the template. Nothing else changes.
- If the offer is blocked for this member, or inactive, or not available on that channel, no draft is made. The dialog shows the reason, for example "This offer is blocked for this member: …" or "This offer is not active".
- Draft requests are not written to the audit log.

## 6. Assistant (W30)

**Who:** every role. **Where:** sidebar, Front desk, **Assistant**, or the round button at the bottom right of any other page.

The assistant answers questions about members, offers and the knowledge graph. It answers only from AnchorAI's own data (the churn model, the rule trace, the graph and, for managers, the weekly plan). When nothing supports an answer it says "I don't know based on the data I have."

### Two ways to open it

- **The page.** A full-height chat with a side panel on wide screens: "What I can answer", "Reading the sources" and a short note on grounding.
- **The floating button.** A side panel that opens over the current page. Use the expand icon in its header to open the full page. The chat is shared between the two, so you keep your conversation. A refresh or **New chat** clears it, and so does signing out.

### Context

The strip above the chat says "Talking about M…" with a link when the assistant has a member in mind, otherwise "No member selected". The member comes from the Member 360 page you are on, or from the last member you asked about. A question that names another member (for example "What about M0042?") uses that one. On Member 360, the button **Ask the assistant about this member** opens the page with that member set.

### Asking

1. Type a question and press Enter. Shift+Enter adds a new line. Questions can be up to 1,000 characters.
2. Or select one of the example questions shown on an empty chat.
3. The answer streams in as it is written.

What it can answer, with an example of each:

| Topic | Example |
|---|---|
| Member risk | "Why is M0155 at risk?" |
| What to offer | "What should we offer M0155?" |
| Compare members | "Compare M0155 with M0042" |
| Member list | "Who are the top 10 members at risk?" |
| Graph impact | "Who is affected by Maya Chen leaving?" |
| Weekly plan (manager and admin) | "What's in this week's plan?" |

After an answer, suggested follow-up questions appear under it, such as "What should we offer M0155?". You can also type your own: "Why those offers?", "Explain that more simply", "What about M0042?". The small tag under each answer shows the topic it understood (for example "Member risk"), the data source used ("via Churn model", "via Rule trace", "via Knowledge graph") and "Follow-up" when it treated the question as a follow-up.

<!-- screenshot: assistant page with an answer, evidence chips and the side panel -->

### Evidence chips

Numbers in the answer are chips that point to the evidence behind that sentence. Their colour shows the kind:

| Kind | Colour | Click opens |
|---|---|---|
| Member data | blue | the member's page |
| Rule | violet | the rule in Rules (admins only) |
| Offer | green | Offers & constraints (admins only) |
| Graph event | amber | Knowledge graph (managers and admins) |
| Weekly plan | teal | the list of sources (managers and admins see plan evidence; staff never do) |

Hover over a chip to read what it says. If your role cannot open the target page, a click scrolls to the matching line under **Show … sources** below the answer. Use that button to list all sources of an answer.

### Rating answers

Select the thumbs-up (Helpful) or thumbs-down (Not helpful) under a grounded answer. You can rate each answer once. Ratings are stored and used to evaluate the assistant. Answers with no evidence cannot be rated.

### Warnings under an answer

| Tag | Meaning |
|---|---|
| No evidence found | Nothing in the data supports an answer, so the assistant did not guess |
| Language model offline | The answer is the evidence lines as they are, not reworded |
| Connection lost, answer may be incomplete | The stream broke part way. Ask again |

### What the assistant cannot do

- It cannot change anything. It does not edit plans, rules, rosters or users, and it does not send messages.
- It cannot answer plan questions for staff. Staff get "Plan details are only available to managers."
- "What if the budget were …" questions need the plan optimiser, which the assistant does not run yet. Use Scenarios instead.
- It does not remember a conversation after a refresh.
- With the language model offline it cannot answer a follow-up that only rewording can handle, and says so.

## 7. Rules (W40)

**Who:** admins. **Where:** sidebar, Administration, **Rules**.

The rule base decides which offers a member may be given. There are three kinds of rule:

| Kind | Does |
|---|---|
| Derive | Concludes a new fact (for example "falling regular") from measured facts |
| Playbook | Proposes an offer on a channel |
| Guardrail | Blocks offers, or all offers |

Guardrails fire first, then higher salience, then more specific rules. Every rule has a mandatory **source** (where the rule comes from).

The header shows the active **Version** number. Under it, a green banner says "Validation passed" or a list of issues (unknown facts, contradictions, unreachable rules). The page has three tabs: **Rules**, **Raw YAML** and **Versions**.

<!-- screenshot: Rules tab with the validation banner and the Test on a member panel -->

### Read the list

The **Rules** tab lists every rule, sorted by salience. Each row shows the description, a code and the source, the kind, the salience, the conditions ("When") and the action ("Then"). Disabled rules are dimmed and marked "Disabled". Search, sort and export work as on other tables.

### Enable or disable a rule

1. Switch the toggle in the **On** column.
2. Add an optional note and confirm. This saves a new version.

### Add or edit a rule

1. Select **New rule**, or **Edit** on a row.
2. Enter the **Rule ID** (new rules only), the **Kind** (new rules only), the **Salience** and a one-sentence **Description**.
3. Enter the **Source** (required).
4. Under **When all of these hold**, build the conditions. Each row is a fact, a comparison and a value. Select **Add condition** for more rows. The fact list shows plain names with the technical name beside them. The value field fits the fact: a number box, a yes/no list, or a list of known choices. A condition the editor cannot show is greyed out with "edit it in the YAML tab".
5. Under **Then**, fill in what the kind needs:
   - Derive: one or more facts to conclude. A derive rule cannot overwrite a measured fact.
   - Playbook: the offer and the channel.
   - Guardrail: **Block all offers**, or **Block specific offers** and pick them.
6. Watch the messages below the form. They validate as you type. The save button stays off until the rule set has no errors.
7. Write a **Note for the version history** (required) and select **Create rule** or **Save rule**.

<!-- screenshot: rule editor dialog with the condition builder -->

### Delete a rule

Select **Delete** on its row, write a note (required) and confirm. You can undo this by rolling back (below).

### Test a rule change on a member

To test a saved rule base on a member:

1. On the **Rules** tab, find **Test on a member**.
2. Enter a member ID (it starts as `M0155`) and select **Run rules**.
3. Read the trace: allowed offers, blocked offers, and the rules fired in order. It is the same trace as on Member 360.

To test a change before you save it:

1. Open the **Raw YAML** tab. It shows the active version.
2. Edit the YAML.
3. Under **Test this draft**, enter a member ID and select **Run draft**. The trace uses your unsaved YAML.
4. Compare it with the result of the saved rules on the **Rules** tab.

### Edit as YAML and save a version

1. On the **Raw YAML** tab, edit the text.
2. Select **Validate**. Parse errors and issues are listed. A green line says "Valid: N rules, no issues."
3. Fill in **Note (required to save)**.
4. Select **Save version**. It is enabled only after a clean validation of the current text. **Revert** puts back the active text.

Every save creates a new version. Nothing is overwritten.

### Someone else saved first

Two admins can edit at once. If another admin saved a version after you opened the page, your save is refused. A warning toast says "Rules changed since you opened them", and the page reloads the latest version. Your edit is not applied. Look at what changed, redo your edit and save again. The same applies to toggles, deletes and activations.

### Version history, compare and rollback

The **Versions** tab lists each version with its note, who saved it, when, and the number of rules. The active one is tagged **Active**.

- **View YAML** opens that version's rules as text.
- **Compare**: click **Compare** on a version. The card below the table shows it against a **Base version** (the active
  version by default; pick any other from the list). It lists the rules added, removed and changed, then the YAML line
  by line: `+` added, `-` removed, with long unchanged runs folded into "… N unchanged lines" (click to expand).
  **Close** hides the card.
- **Activate** on an older version rolls the rule base back to it after you confirm. Plans and traces use it straight away. Rolling back adds an audit entry. It does not delete newer versions.

<!-- screenshot: Versions tab -->

### Guardrails in plan review

Guardrails are not only shown here. When a manager overrides or adds a contact in plan review, AnchorAI runs the proposed offer for that member through the active rule base. A violation (a blocked offer, an inactive offer, or an offer not available on that channel) is shown next to the item. This is why a guardrail rule you add takes effect on the next plan review check.

### Links from the assistant

A rule chip in an assistant answer opens this page with that rule highlighted, for admins.

## 8. Users (W43)

**Who:** admins. **Where:** sidebar, Administration, **Users**.

The table lists name, username, role, status and creation date. You are marked "(you)".

To create a user:

1. Select **Add user**.
2. Enter a username (3 to 40 letters, digits, dots, dashes or underscores), a full name, a role and a password of at least 8 characters.
3. Select **Create user**. Share the password securely. It is not shown again.

To change a role or name: select **Edit** on the row, change the fields and select **Save changes**. A role change applies at the user's next request, without signing out.

To deactivate a user: select **Edit**, switch off **Active (can sign in)** and save. The user is signed out at their next request and cannot sign in. Switch it on again to restore them. Users are never deleted, so the audit log stays complete.

To reset a password: select **Reset password**, enter a new password of at least 8 characters and confirm. This signs the user out on every device. They sign in again with the new password.

Rules the page enforces:

- You cannot change your own role or deactivate your own account.
- The last active admin cannot be demoted or deactivated. The page shows the reason.
- A username that already exists is refused ("Username … is taken").

Every change is written to the audit log.

<!-- screenshot: Users page with the edit dialog -->

## 9. Audit log (W44)

**Who:** admins. **Where:** sidebar, Administration, **Audit log**.

The audit log is a record of who did what and when. Entries are added by the application and cannot be edited here.

What is recorded:

| Area | Examples |
|---|---|
| Sign-in | every successful login |
| Users | create, update (role, name, active), password reset |
| Rules | new version saved, version activated (rollback) |
| Roster and events | add instructor, add class, reassign class, record event, revoke event |
| Knowledge graph | reload, failed reload |
| Offers and constraints, data | offer deleted, staff hours updated, constraints updated, data upload, data rebuild |
| Assistant | thumbs-up or thumbs-down |

Plan approval, overrides, assignments and outcomes are written by Stream B's pages and appear here too.

To read the log:

1. Each row shows when, who, the action, what it was done to (with its ID), and a one-line **Change**.
2. Select the change text to open **Before** and **After** side by side.
3. The newest entries are first. The table pages 25 entries at a time.

To filter, use **All actions** and **All users** at the top of the table. Clear a filter with the cross.

To export, use the table's export button. It downloads every entry that matches the current filters as `audit-log.csv`.

<!-- screenshot: Audit log filtered to rule changes with the before and after open -->

## 10. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| "Knowledge graph unavailable" on the Knowledge graph page or in a Member 360 panel | Neo4j is not running. Start it (`docker compose up -d neo4j`), then select **Reload knowledge graph** on the Events & roster page. The rest of the app keeps working |
| "Edits are saved, but the knowledge graph has not been rebuilt from them" | A roster edit was made while Neo4j was down. Start Neo4j and select **Reload knowledge graph** |
| Rules that use graph signals (lost instructor, cancelled class) do not fire | The graph was never loaded or is stale. Run `uv run anchorai kg load`, or reload from the page |
| Assistant says "Language model offline" and shows plain evidence lines | The LLM endpoint in `.env` is unreachable. Answers are still correct, only not reworded. Check `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL` |
| Message drafts always say "Template" | The language model is offline, or its text was rejected by the checks in section 5. This is expected |
| The assistant says "I don't know based on the data I have." | Nothing in the data answers the question. Name a member (`M0155`), or ask one of the topics in section 6 |
| First assistant question is slow | The embedding model downloads once (about 90 MB). After that it runs offline |
| Assistant page shows an error such as "Data tables are not built yet" | Run `uv run anchorai data build` |
| "Rules changed since you opened them" | Another admin saved a version first. The page has reloaded the latest rules. Redo your change and save |
| Save version is greyed out in Raw YAML | You have not changed the text, you have not validated it, validation found errors, or the note is empty |
| Signed out unexpectedly | The session lasted 12 hours, your password was reset, or your account was deactivated. Sign in again |
| A demo user cannot sign in | Run `uv run anchorai db reset` to restore the seeded users |
