import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { AuthLayout } from '@/components/layout/AuthLayout'
import { FormInput } from '@/components/ui/FormInput'
import { Button } from '@/components/ui/Button'
import { loginSchema, type LoginFormValues } from '@/lib/validators'
import { useAuth } from '@/hooks/useAuth'

export default function Login() {
    const { login, isLoggingIn, loginError } = useAuth()

    const {
        register,
        handleSubmit,
        formState: { errors },
    } = useForm<LoginFormValues>({ resolver: zodResolver(loginSchema) })

    function onSubmit(data: LoginFormValues) {
        login(data)
    }

    return (
        <AuthLayout title="Welcome back" subtitle="Log in to view your placement analysis">
            <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
                <FormInput
                    label="Email"
                    type="email"
                    placeholder="you@college.edu"
                    error={errors.email?.message}
                    {...register('email')}
                />
                <FormInput
                    label="Password"
                    type="password"
                    placeholder="Your password"
                    error={errors.password?.message}
                    {...register('password')}
                />

                {loginError && (
                    <p className="text-sm text-red-500 bg-red-50 rounded-lg px-3 py-2">
                        {(loginError as any).response?.data?.detail || (loginError as Error).message || 'Login failed. Please check credentials.'}
                    </p>
                )}

                <Button type="submit" isLoading={isLoggingIn} className="w-full mt-2">
                    Log In
                </Button>
            </form>

            <p className="mt-6 text-center text-sm text-slate-500">
                Don't have an account?{' '}
                <Link to="/register" className="text-indigo-600 font-medium hover:underline">
                    Register
                </Link>
            </p>
        </AuthLayout>
    )
}
