import axios from "axios"
import { useEffect, useState } from "react"
import { useCallback } from "react/cjs/react.development"

export const useQuery = ({ query, variables, consumeData, ignore }) => {
   const [loading, setLoading] = useState(false)

   useEffect(() => {
      if (!ignore) {
         let cancelRequest

         setLoading(true)

         axios({
            url: '/graphql',
            method: 'post',
            data: { query, variables },
            cancelToken: new axios.CancelToken(cancel => cancelRequest = cancel)
         }).then(response => {
            setLoading(false)
            consumeData(response.data.data)
         }).catch(error => {
            if (axios.isCancel(error)) {
               return
            }
         })

         return () => {
            cancelRequest()
         }
      }
   }, [query, variables, consumeData, ignore])

   return loading
}

export const useMutation = ({ query }) => {
   const [loading, setLoading] = useState(false)

   const mutation = useCallback(({ variables, consumeData }) => {
      axios({
         url: '/graphql',
         method: 'post',
         data: { query, variables },
      }).then(response => {
         setLoading(false)
         if (consumeData) {
            consumeData(response.data.data)
         }
      })
   }, [query])

   return [mutation, loading]
}
