"""OpenCart MCP Server — query and manage OpenCart via Claude Code."""

import json
import re

# import shlex

# from fastmcp import FastMCP
from langchain_core.tools import tool

from config import Config
from db import OpenCartDB
from dotenv import load_dotenv

load_dotenv(override=True)
config = Config.from_env()
db = OpenCartDB(config)


def esc(s: str) -> str:
    """Escape a value for interpolation into a single-quoted MySQL string.
    Backslash first, then quote — MySQL consumes backslash escapes."""
    return s.replace("\\", "\\\\").replace("'", "\\'")


@tool
def search_products(
    search: str = "",
    category_id: int = 0,
    limit: int = 50,
    include_description: bool = False,
) -> str:
    """List products with stock, prices, and SEO data.
    Search by name. Optionally filter by category_id.
    Set include_description=True to include full HTML descriptions.
    Args:
        search: Search text to match product names.
        category_id: Optional category ID to filter products.
        limit: Maximum number of products to return (default 50).
        include_description: Whether to include full product descriptions (default False).
    Returns:
        JSON array of product objects, each with fields:
            product_id, name, model, sku, price, quantity,
            stock_status_id, status, date_modified, weight, image,
            seo_url, meta_title, meta_description, and optionally description."""

    where = "WHERE p.status = 1"
    if search:
        safe = esc(search)
        where += f" AND pd.name LIKE '%{safe}%'"
    if category_id:
        where += f" AND p.product_id IN (SELECT product_id FROM oc_product_to_category WHERE category_id = {int(category_id)})"

    desc_col = ", pd.description" if include_description else ""

    sql = f"""
        SELECT p.product_id, pd.name, p.model, p.sku, p.price, p.quantity,
               p.stock_status_id, p.status, p.date_modified,
               p.weight, p.image,
               su.keyword AS seo_url,
               pd.meta_title, pd.meta_description{desc_col}
        FROM oc_product p
        JOIN oc_product_description pd ON p.product_id = pd.product_id AND pd.language_id = 2
        LEFT JOIN oc_seo_url su ON su.query = CONCAT('product_id=', p.product_id) AND su.language_id = 2
        {where}
        ORDER BY pd.name
        LIMIT {int(limit)}
    """
    rows = db.run_query(sql)
    return json.dumps(rows)
