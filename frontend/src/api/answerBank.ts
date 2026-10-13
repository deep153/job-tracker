import type { BankEntry, BankEntryIn } from "../types/answers";
import { request, sendJson } from "./client";

export const listAnswers = () => request<BankEntry[]>("/api/answer-bank");

export const addAnswer = (entry: BankEntryIn) => request<BankEntry>("/api/answer-bank", sendJson("POST", entry));

export const updateAnswer = (id: number, entry: BankEntryIn) =>
  request<BankEntry>(`/api/answer-bank/${id}`, sendJson("PUT", entry));

export const deleteAnswer = (id: number) => request<void>(`/api/answer-bank/${id}`, { method: "DELETE" });
