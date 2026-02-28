import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/Button'

export function Navbar() {
    const { isAuthenticated, logout } = useAuth()
    const navigate = useNavigate()

    return (
        <nav className="sticky top-0 z-40 bg-white/90 backdrop-blur border-b border-slate-100">
            <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
                <Link to="/" className="flex items-center gap-2 font-semibold text-slate-900">
                    <span className="text-indigo-600 text-xl"></span>
                    <span>CampusHire Advisor</span>
                </Link>

                <div className="flex items-center gap-3">
                    {isAuthenticated ? (
                        <>
                            <Button variant="ghost" size="sm" onClick={() => navigate('/profile')}>
                                Dashboard
                            </Button>
                            <Button variant="outline" size="sm" onClick={() => logout()}>
                                Logout
                            </Button>
                        </>
                    ) : (
                        <>
                            <Button variant="ghost" size="sm" onClick={() => navigate('/login')}>
                                Login
                            </Button>
                            <Button size="sm" onClick={() => navigate('/register')}>
                                Get Started
                            </Button>
                        </>
                    )}
                </div>
            </div>
        </nav>
    )
}
