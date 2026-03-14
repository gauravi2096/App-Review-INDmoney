/**
 * Email sending via nodemailer (SMTP or SMTP URL).
 * Sends HTML body with optional reply-to.
 */

import nodemailer from 'nodemailer';
import config from './config.js';

let transporter = null;

function getTransporter() {
  if (transporter) return transporter;
  if (config.smtpUrl) {
    transporter = nodemailer.createTransport(config.smtpUrl);
  } else {
    transporter = nodemailer.createTransport({
      host: config.smtpHost,
      port: config.smtpPort,
      secure: config.smtpSecure,
      auth: config.smtpUser ? { user: config.smtpUser, pass: config.smtpPass } : undefined,
    });
  }
  return transporter;
}

/**
 * Send one email.
 * @param {{ to: string, subject: string, html: string, replyTo?: string }} opts
 * @returns {Promise<{ success: boolean, error?: string }>}
 */
export async function sendEmail({ to, subject, html, replyTo }) {
  try {
    const transport = getTransporter();
    const from = config.fromAddress;
    await transport.sendMail({
      from,
      to,
      replyTo: replyTo || config.replyTo || from,
      subject,
      html,
    });
    return { success: true };
  } catch (err) {
    return { success: false, error: err?.message || String(err) };
  }
}
