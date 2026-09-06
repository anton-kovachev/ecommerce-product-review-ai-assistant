---
name: product-search
description: Search for product by name, brand product code and product type.
---

# Product Information Research

## When to use

Use this skill when an information about a product is requested to search and find the requested information.

## Research style

- Extract the product name, brand name, product code or product type from the user query if avaiable.
  - example: "Tell me about the chainsaw STIHL MS 661" -> product type: "chainsaw", brand name: "STIHL", product name: "MS 661"
- Use the product search tool to find the product and get its description, features, images, price, etc. performing several search on the product name, brand name, product code or product type if available or search on combinations i.e. {product-brand} {product-name}.
  - example: "chainsaw STIHL MS 661" -> search for "chainsaw STIHL MS 661", "STIHL MS 661", "STIHL chainsaw", "MS 661 chainsaw", "MS 661", etc.
  - example: "trimmer FS 131 by STIHL" -> search for "FS 131", "STIHL FS 131", "STIHL trimmer", "FS 131 trimmer", etc.
  - Always try to find the most relevant product by performing multiple calls to search products with different keywords and then comparing the product name, brand name, product code or product type with the search results.
  - If the product search tool returns no results, try to search for the product using different combinations of the product name, brand name, product code or product type.
  - If the product search tool returns multiple results, try to find the most relevant product by comparing the product name, brand name, product code or product type with the search results.

## Workflow

1. Analyze the provided user query and identify the product name or brand name to search for.
2. User the product search tool to find the product and get its description, features, images, price, etc.
3. Don't search the web for products, and don't use the browser for product searches only use trhe search products tool.
