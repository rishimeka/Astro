"use client";
import React from "react";

type RequestAccessContextType = {
    open: (email?: string) => void;
    close: () => void;
    isOpen: boolean;
    initialEmail: string;
    setInitialEmail: (email: string) => void;
};

const RequestAccessContext = React.createContext<RequestAccessContextType | null>(null);

export const RequestAccessProvider = ({ children }: { children: React.ReactNode }) => {
    const [isOpen, setIsOpen] = React.useState(false);
    const [initialEmail, setInitialEmail] = React.useState("");

    const open = (email?: string) => {
        if (email) setInitialEmail(email);
        setIsOpen(true);
    };

    const close = () => {
        setIsOpen(false);
        setInitialEmail("");
    };

    return (
        <RequestAccessContext.Provider value={{ open, close, isOpen, initialEmail, setInitialEmail }}>
            {children}
        </RequestAccessContext.Provider>
    );
};

export const useRequestAccess = () => {
    const ctx = React.useContext(RequestAccessContext);
    if (!ctx) throw new Error("useRequestAccess must be used within RequestAccessProvider");
    return ctx;
};
