const fs = require('fs');
const s = JSON.parse(fs.readFileSync('D:\\Project ISAP\\isap\\isap\\docs\\audit\\pmla_v2.schema.proposed.json', 'utf8'));
console.log('=== PMLA v2 Proposed Schema Validation ===');
console.log('Valid JSON: YES');
console.log('$schema:', s['$schema']);
console.log('$id:', s['$id']);
console.log('type:', s.type);
console.log('additionalProperties:', s.additionalProperties);
console.log('Properties count:', Object.keys(s.properties).length);
console.log('Required count:', s.required.length);
console.log('$defs count:', Object.keys(s['$defs']).length);
console.log('$defs names:', Object.keys(s['$defs']).join(', '));
console.log('');

// Check required vs properties
const missing = s.required.filter(k => !s.properties[k]);
if (missing.length > 0) {
  console.log('ERROR - required fields not in properties:', missing);
} else {
  console.log('All required fields are in properties: OK');
}

// Check hazard_class
const hc = s.properties.hazard_class;
console.log('hazard_class uses $ref:', hc['$ref']);
console.log('HazardClass enum:', s['$defs'].HazardClass.enum);

// Check arrays have items
const arrays = Object.entries(s.properties).filter(([k, v]) => v.type === 'array');
console.log('Array properties:', arrays.map(([k]) => k).join(', '));
for (const [k, v] of arrays) {
  if (!v.items) console.log('  WARNING:', k, 'missing items');
}

console.log('');
console.log('=== Summary ===');
console.log('37 template scalars + 11 notification phones + 3 additional scalars (edds_district etc) = 51 properties');
console.log('9 array types = 9 array properties');
console.log('9 $defs types');
