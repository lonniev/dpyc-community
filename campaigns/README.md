# Pricing Campaigns

Shared pricing campaign designs from the DPYC community.

Each campaign is a pricing strategy designed through the Pricing Studio's
AI-guided structured interview. Campaigns are published here so operators
can learn from each other's pricing strategies and import proven designs
into their own services.

## Structure

Campaigns are organized by author and target operator:

```
campaigns/
  {author_npub}/
    {operator_npub}/
      {campaign-slug}/
        campaign.json       # Machine-importable — load into Pricing Studio
        campaign.md         # Human-readable summary with rationale
```

- **author_npub** — the person who designed the campaign
- **operator_npub** — the operator the campaign was designed for
- **campaign-slug** — a URL-safe name derived from the campaign title

### campaign.json

The full campaign export: operator context, tool prices, constraint pipeline
steps, revenue projections, and interview analysis. Import this directly
into Pricing Studio to adopt or adapt the campaign.

### campaign.md

A readable narrative explaining the campaign's pricing philosophy, what
constraints it uses, why, and what the projected economics look like.
Read this to understand whether the strategy fits your service before
importing.

## Borrowing Campaigns

A campaign designed for one operator may inspire another. The tool prices
and constraint pipeline are operator-specific (different tools, different
economics), so a direct import won't work. A future "Reconcile" feature
in Pricing Studio will assist with adapting a campaign from one operator's
tool catalog to another's.

## Publishing

Use the Oracle's `publish_campaign` tool or the Share button in Pricing
Studio. Both produce the JSON and Markdown exports.

## License

Campaign designs shared here are Apache-2.0 licensed, consistent with
the rest of the DPYC ecosystem.
