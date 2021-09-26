import React, { useCallback, useContext, useEffect, useMemo, useState } from "react"
import { useSessionContext } from "./Session"

const ControllerContext = React.createContext()

export const Controller = ({ setShowSideNav, children }) => {
   const { entries, refresh } = useSessionContext()
   const entriesLength = entries.length

   const [activeEntryIndex, setActiveEntryIndex] = useState(-1)
   const [showEntry, setShowEntry] = useState(false)

   useEffect(() => {
      const onKeyDown = event => {
         const key = event.which
         if (key === 66/*b*/ && activeEntryIndex !== -1) {
            // TODO: toggle bliss
         } else if (key === 74/*j*/ && entriesLength) {
            setActiveEntryIndex(Math.min(entriesLength - 1, activeEntryIndex + 1))
            setShowEntry(true)
         } else if (key === 75/*k*/ && entriesLength) {
            setActiveEntryIndex(Math.max(0, activeEntryIndex - 1))
            setShowEntry(true)
         } else if (key === 77/*m*/ && activeEntryIndex !== -1) {
            // TODO: toggle read/pinned
         } else if (key === 78/*n*/ && entriesLength) {
            setActiveEntryIndex(Math.min(entriesLength - 1, activeEntryIndex + 1))
         } else if (key === 79/*o*/ && activeEntryIndex !== -1) {
            setShowEntry(showEntry => !showEntry)
         } else if (key === 80/*p*/ && entriesLength) {
            setActiveEntryIndex(Math.max(0, activeEntryIndex - 1))
         } else if (key === 82/*r*/) {
            refresh()
         } else if (key === 83/*s*/ && activeEntryIndex !== -1) {
            // TODO: toggle star
         }
      }

      window.addEventListener('keydown', onKeyDown)

      return () => {
         window.removeEventListener('keydown', onKeyDown)
      }
   }, [activeEntryIndex, entriesLength, refresh])

   const onFeedClick = useCallback(() => {
      refresh()
      setShowSideNav(false)
   }, [refresh, setShowSideNav])

   const controller = useMemo(() => ({ activeEntryIndex, setActiveEntryIndex, showEntry, setShowEntry, onFeedClick }), [activeEntryIndex, setActiveEntryIndex, showEntry, setShowEntry, onFeedClick])

   return (
      <ControllerContext.Provider value={controller}>
         {children}
      </ControllerContext.Provider>
   )
}

export const useController = () => useContext(ControllerContext)
