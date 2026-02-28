import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { AuthLayout } from '@/components/layout/AuthLayout'
import { FormInput } from '@/components/ui/FormInput'
import { Button } from '@/components/ui/Button'
import { registerSchema, type RegisterFormValues } from '@/lib/validators'
import { useAuth } from '@/hooks/useAuth'

export default function Register() {
    const { register: registerUser, isRegistering, registerError } = useAuth()

    const {
        register,
        handleSubmit,
        formState: { errors },
    } = useForm<RegisterFormValues>({ resolver: zodResolver(registerSchema) })

    function onSubmit(data: RegisterFormValues) {
        registerUser({ name: data.name, email: data.email, password: data.password })
    }

    return (
        <AuthLayout title="Create your account" subtitle="Start analysing your placement readiness">
            <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
                <FormInput label="Full Name" placeholder="Riya Sharma" error={errors.name?.message} {...register('name')} />
                <FormInput label="College Email" type="email" placeholder="you@college.edu" error={errors.email?.message} {...register('email')} />
                <FormInput label="Password" type="password" placeholder="Min 8 chars, 1 uppercase, 1 number" error={errors.password?.message} {...register('password')} />
                <FormInput label="Confirm Password" type="password" placeholder="Repeat password" error={errors.confirmPassword?.message} {...register('confirmPassword')} />

                {/* Consent */}
                <label className="flex items-start gap-3 cursor-pointer">
                    <input type="checkbox" className="mt-0.5 accent-indigo-600" {...register('consent')} />
                    <span className="text-sm text-slate-600">
                        I agree to my data being stored anonymously for analysis and model improvement.{' '}
                        <a href="#" className="text-indigo-600 underline">Privacy Policy</a>
                    </span>
                </label>
                {errors.consent && <p className="text-xs text-red-500">{errors.consent.message}</p>}

                {registerError && (
                    <p className="text-sm text-red-500 bg-red-50 rounded-lg px-3 py-2">
                        {(registerError as any).response?.data?.detail || (registerError as Error).message || 'Registration failed. Please try again.'}
                    </p>
                )}

                <Button type="submit" isLoading={isRegistering} className="w-full mt-2">
                    Create Account
                </Button>
            </form>

            <p className="mt-6 text-center text-sm text-slate-500">
                Already have an account?{' '}
                <Link to="/login" className="text-indigo-600 font-medium hover:underline">
                    Login
                </Link>
            </p>
        </AuthLayout>
    )
}
