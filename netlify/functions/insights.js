// Serverless AI-insights endpoint. Takes a report summary, asks Claude for a
// concise facility assessment, and returns the text. This is a short, stateless
// call — a good fit for serverless — so it works on the deployed Netlify site
// (unlike the heavier Python chat backend). The API key stays server-side
// (Netlify env var ANTHROPIC_API_KEY); it is never sent to the browser.

import Anthropic from '@anthropic-ai/sdk';
import { INSIGHTS_SYSTEM, summarizeReport } from '../../src/lib/insightsPrompt.js';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Content-Type': 'application/json',
};

export const handler = async (event) => {
  if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers: CORS, body: '' };
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, headers: CORS, body: JSON.stringify({ error: 'Use POST.' }) };
  }
  if (!process.env.ANTHROPIC_API_KEY) {
    return {
      statusCode: 500,
      headers: CORS,
      body: JSON.stringify({ error: 'AI insights unavailable: ANTHROPIC_API_KEY is not set on the server.' }),
    };
  }

  try {
    const report = JSON.parse(event.body || '{}');
    const client = new Anthropic();
    const msg = await client.messages.create({
      model: process.env.CHAT_MODEL || 'claude-opus-4-8',
      max_tokens: 500,
      system: INSIGHTS_SYSTEM,
      messages: [{ role: 'user', content: summarizeReport(report) }],
    });
    const insight = (msg.content || [])
      .filter((b) => b.type === 'text')
      .map((b) => b.text)
      .join('')
      .trim();
    return { statusCode: 200, headers: CORS, body: JSON.stringify({ insight }) };
  } catch (e) {
    return { statusCode: 502, headers: CORS, body: JSON.stringify({ error: `AI insight failed: ${e.message || e}` }) };
  }
};
