// Copyright 2026 Trieflow LLC. MIT.
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Text;

namespace BeatQuayQualification {
    public static class ApiSetResolver {
        [DllImport("api-ms-win-core-apiquery-l2-1-0.dll", CharSet = CharSet.Ansi, ExactSpelling = true)]
        [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool IsApiSetImplemented(string contract);

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, ExactSpelling = true, SetLastError = true)]
        [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
        private static extern IntPtr LoadLibraryExW(string name, IntPtr file, uint flags);

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, ExactSpelling = true, SetLastError = true)]
        [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
        private static extern uint GetModuleFileNameW(IntPtr module, StringBuilder path, uint size);

        [DllImport("kernel32.dll", ExactSpelling = true, SetLastError = true)]
        [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool FreeLibrary(IntPtr module);

        public static string Resolve(string name) {
            // The caller validates the complete immutable contract, including .dll.
            if (!IsApiSetImplemented(name.Substring(0, name.Length - 4)))
                throw new InvalidOperationException("API set is not implemented on this OS: " + name);
            const uint LOAD_LIBRARY_SEARCH_SYSTEM32 = 0x00000800;
            IntPtr module = LoadLibraryExW(name, IntPtr.Zero, LOAD_LIBRARY_SEARCH_SYSTEM32);
            if (module == IntPtr.Zero) throw new Win32Exception(Marshal.GetLastWin32Error(), "API-set host could not load: " + name);
            try {
                var path = new StringBuilder(32768);
                uint length = GetModuleFileNameW(module, path, (uint)path.Capacity);
                if (length == 0 || length >= path.Capacity)
                    throw new Win32Exception(Marshal.GetLastWin32Error(), "API-set host path could not be observed: " + name);
                return path.ToString();
            } finally {
                if (!FreeLibrary(module)) throw new Win32Exception(Marshal.GetLastWin32Error(), "API-set host handle could not be released");
            }
        }
    }
}
