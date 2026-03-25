import { z } from 'zod'

// ─── Step 1: Profile & Usernames ─────────────────────────────────────────────
export const profileSchema = z.object({
    tenthPct: z.number().min(0).max(100),
    twelfthPct: z.number().min(0).max(100),
    cgpa: z.number().min(0),
    cgpaScale: z.union([z.literal(10), z.literal(4)]),
    branch: z.string().min(1, 'Select a branch'),
    year: z.number().min(1).max(4),
    backlogs: z.number().min(0),

    // Required platforms
    leetcodeUsername: z.string().min(1, 'LeetCode username is required'),
    githubUsername: z.string().min(1, 'GitHub username is required'),
    codeforcesHandle: z.string().min(1, 'Codeforces handle is required for accurate prediction'),

    // Optional (free API unreliable — we try but don't block)
    codechefUsername: z.string(),
})

export type ProfileFormValues = z.infer<typeof profileSchema>

// ─── Auth ─────────────────────────────────────────────────────────────────────
export const registerSchema = z
    .object({
        name: z.string().min(2, 'Name must be at least 2 characters'),
        email: z.string().email('Enter a valid email address'),
        password: z
            .string()
            .min(8, 'At least 8 characters')
            .regex(/[A-Z]/, 'Must contain an uppercase letter')
            .regex(/[0-9]/, 'Must contain a number'),
        confirmPassword: z.string(),
        consent: z.literal(true, 'You must agree to continue'),
    })
    .refine((d) => d.password === d.confirmPassword, {
        message: 'Passwords do not match',
        path: ['confirmPassword'],
    })

export const loginSchema = z.object({
    email: z.string().email('Enter a valid email address'),
    password: z.string().min(1, 'Password is required'),
})

export type RegisterFormValues = z.infer<typeof registerSchema>
export type LoginFormValues = z.infer<typeof loginSchema>


// ─── NEW: LOR Schema ─────────────────────────────────────────
export const lorSchema = z.object({
  source_type: z.enum(['industry', 'academic_strong', 'academic_standard']),
  institution: z.string().optional(),
})

// ─── NEW: Hackathon Certificate Schema ───────────────────────
export const hackathonCertSchema = z.object({
  event_name: z.string().min(2, 'Enter the event name'),
  prize_level: z.enum(['first', 'second', 'third', 'participation']),
})

// ─── NEW: Step 3b Schema ─────────────────────────────────────
export const step3bSchema = z.object({
  lors: z.array(lorSchema).max(3),
  hackathon_certs: z.array(hackathonCertSchema).max(10),
})

// ─── Types (IMPORTANT for TS) ─────────────────────────────────
export type Lor = z.infer<typeof lorSchema>
export type HackathonCert = z.infer<typeof hackathonCertSchema>
export type Step3bFormValues = z.infer<typeof step3bSchema>
