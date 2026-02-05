#!/bin/bash

# Test the admin map-sources page

echo "Testing admin page..."
echo ""

# Check if scanlators endpoint works
echo "1. Testing scanlators endpoint:"
curl -sL "http://localhost:8008/api/scanlators/?active_only=true" | python3 -c "import sys, json; data = json.load(sys.stdin); print(f'  ✓ Found {len(data)} active scanlator(s)')"
echo ""

# Check if unmapped manga endpoint works
echo "2. Testing unmapped manga endpoint:"
SCANLATOR_ID=$(curl -sL "http://localhost:8008/api/scanlators/?active_only=true" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data[0]['id'])" 2>/dev/null)
curl -sL "http://localhost:8008/api/manga/unmapped?scanlator_id=${SCANLATOR_ID}" | python3 -c "import sys, json; data = json.load(sys.stdin); print(f'  ✓ Found {data[\"count\"]} unmapped manga for {data[\"scanlator_name\"]}')"
echo ""

# Check if frontend page loads
echo "3. Testing frontend page:"
HTTP_CODE=$(curl -sL -w "%{http_code}" "http://localhost:4343/admin/map-sources" -o /dev/null)
if [ "$HTTP_CODE" -eq 200 ]; then
    echo "  ✓ Page loads successfully (HTTP $HTTP_CODE)"
else
    echo "  ✗ Page failed to load (HTTP $HTTP_CODE)"
fi
echo ""

echo "All tests completed!"
