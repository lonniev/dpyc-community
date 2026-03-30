# Pricing Campaigns

Shared pricing campaign designs from the DPYC community.

Each campaign is a pricing strategy designed through the Pricing Studio's
AI-guided structured interview. Campaigns are published here so operators
can learn from each other's pricing strategies and import proven designs
into their own services.

## Structure

Each campaign is a directory containing:

```
campaigns/
  acme-weather-freemium/
    campaign.json       # Machine-importable — load into Pricing Studio
    campaign.md         # Human-readable summary with rationale
```

### campaign.json

The full campaign export: operator context, tool prices, constraint pipeline
steps, revenue projections, and interview analysis. Import this directly
into Pricing Studio to adopt or adapt the campaign.

### campaign.md

A readable narrative explaining the campaign's pricing philosophy, what
constraints it uses, why, and what the projected economics look like.
Read this to understand whether the strategy fits your service before
importing.

## Contributing

Export a campaign from Pricing Studio using the Share button, then submit
a pull request adding your campaign directory here. Include both the JSON
and Markdown exports.

## License

Campaign designs shared here are Apache-2.0 licensed, consistent with
the rest of the DPYC ecosystem.
