
export default function Navbar() {
  return (
    <nav className="bg-white border-b shadow-sm px-6 py-4 flex justify-between">
      <span className="font-bold text-lg">DockMate</span>
      <div className="space-x-4">
        <a href="/" className="text-blue-600 hover:underline">Dashboard</a>
        <a href="/login" className="text-blue-600 hover:underline">Login</a>
        <a href="/signup" className="text-white bg-blue-600 px-3 py-2 rounded-md">Signup</a>
      </div>
    </nav>
  );
}
